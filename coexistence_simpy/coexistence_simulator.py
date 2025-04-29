import logging
import csv
import os
import random
import simpy
from dataclasses import dataclass, field
from typing import Dict, List
from .radio_parameters import Times

# Configuration constants
MAX_TRANSMISSION_PRIORITY = 100000

# GAP_MODE_ENABLED = False

# Simplify logging
logging.basicConfig(format='%(asctime)s %(message)s', filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

LOG_COLORS = ["\033[32m", "\033[31m", "\033[33m", "\033[34m", "\033[35m", "\033[36m", "\033[37m"]

class ChannelBusyError(Exception):
    pass

@dataclass()
class WiFiConfig:
    data_size: int = 1472
    min_cw: int = 15
    max_cw: int = 63
    r_limit: int = 7
    mcs: int = 7

@dataclass()
class NRUConfig:
    prioritization_period_us: int = 16
    observation_slot_duration: int = 9
    synchronization_slot_duration: int = 1000
    max_sync_slot_desync: int = 1000
    min_sync_slot_desync: int = 0
    M: int = 3
    min_cw: int = 15
    max_cw: int = 63
    mcot: int = 6

def log_transmission_event(node, mes: str) -> None:
    logger.info(f"{node.log_color}Time: {node.env.now} Station: {node.name} Message: {mes}")

def generate_desync_offsets(max, number, min_distance=0):
    samples = random.sample(range(max - (number - 1) * (min_distance - 1)), number)
    indices = sorted(range(len(samples)), key=lambda i: samples[i])
    ranks = sorted(indices, key=lambda i: indices[i])
    return [sample + (min_distance - 1) * rank for sample, rank in zip(samples, ranks)]

@dataclass()
class WiFiDataPacket:
    frame_time: int
    station_name: str
    log_color: str
    data_size: int
    start_time_us: int
    number_of_retransmissions: int = 0
    end_time_us: int = None
    transmission_duration_us: int = None

@dataclass()
class NRUTransmission:
    transmission_time: int
    enb_name: str
    log_color: str
    start_time_us: int
    airtime: int
    rs_time: int
    number_of_retransmissions: int = 0
    end_time_us: int = None
    transmission_duration_us: int = None
    collided: bool = False

@dataclass()
class WirelessMedium:
    tx_queue: simpy.PreemptiveResource
    tx_lock: simpy.Resource
    num_wifi_stations: int
    num_nru_nodes: int
    backoff_counts: Dict[int, Dict[int, int]]
    data_airtime: Dict[str, int]
    control_airtime: Dict[str, int]
    airtime_data_NR: Dict[str, int]
    airtime_control_NR: Dict[str, int]
    active_wifi_transmitters: List = field(default_factory=list)
    wifi_stations_in_backoff: List = field(default_factory=list)
    active_nru_transmitters: List = field(default_factory=list)
    nru_nodes_in_backoff: List = field(default_factory=list)
    failed_transmissions: int = 0
    succeeded_transmissions: int = 0
    bytes_sent: int = 0
    failed_transmissions_NR: int = 0
    succeeded_transmissions_NR: int = 0

class WiFiStation:
    def __init__(self, env, name, channel, config=WiFiConfig()):
        self.config = config
        self.times = Times(config.data_size, config.mcs)
        self.name = name
        self.env = env
        self.log_color = random.choice(LOG_COLORS)
        self.frame_to_send = None
        self.succeeded_transmissions = 0
        self.failed_transmissions = 0
        self.failed_transmissions_in_row = 0
        self.min_cw = config.min_cw
        self.max_cw = config.max_cw
        self.channel = channel
        self.process = None
        self.first_interrupt = False
        self.back_off_time = 0
        self.start = 0

        self.channel.data_airtime.update({name: 0})
        self.channel.control_airtime.update({name: 0})
        env.process(self.start_process())

    def start_process(self):
        while True:
            self.frame_to_send = self.generate_wifi_frame()
            was_sent = False
            while not was_sent:
                self.process = self.env.process(self.wait_back_off())
                yield self.process
                was_sent = yield self.env.process(self.send_frame())

    def wait_back_off(self):
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)

        while self.back_off_time > -1:
            try:
                with self.channel.tx_lock.request() as req:
                    yield req
                self.back_off_time += Times.t_difs
                log_transmission_event(self, f"Starting to wait backoff (with DIFS): ({self.back_off_time})u...")
                self.first_interrupt = True
                self.start = self.env.now
                self.channel.wifi_stations_in_backoff.append(self)

                yield self.env.timeout(self.back_off_time)
                log_transmission_event(self, f"Backoff waited, sending frame...")
                self.back_off_time = -1

                self.channel.wifi_stations_in_backoff.remove(self)

            except simpy.Interrupt:
                if self.first_interrupt and self.start is not None:
                    log_transmission_event(self, "Waiting was interrupted, waiting to resume backoff...")
                    all_waited = self.env.now - self.start
                    if all_waited <= Times.t_difs:
                        self.back_off_time -= Times.t_difs
                    else:
                        slot_waited = int((all_waited - Times.t_difs) / Times.t_slot)
                        self.back_off_time -= ((slot_waited * Times.t_slot) + Times.t_difs)
                    self.first_interrupt = False

    def send_frame(self):
        self.channel.active_wifi_transmitters.append(self)
        res = self.channel.tx_queue.request(priority=(MAX_TRANSMISSION_PRIORITY - self.frame_to_send.frame_time))

        try:
            result = yield res | self.env.timeout(0)
            if res not in result:
                raise simpy.Interrupt("There is a longer frame...")

            with self.channel.tx_lock.request() as lock:
                yield lock

                self.interrupt_backoff_stations()

                log_transmission_event(self, f'Starting sending frame: {self.frame_to_send.frame_time}')
                yield self.env.timeout(self.frame_to_send.frame_time)
                self.channel.wifi_stations_in_backoff.clear()

                was_sent = self.check_for_collision()

                if was_sent:
                    self.channel.control_airtime[self.name] += self.times.get_ack_frame_time()
                    yield self.env.timeout(self.times.get_ack_frame_time())
                    self.clear_transmission_state(res)
                    return True

                self.clear_transmission_state(res)
                self.channel.tx_queue = simpy.PreemptiveResource(self.env, capacity=1)
                yield self.env.timeout(self.times.ack_timeout)
                return False

        except simpy.Interrupt:
            yield self.env.timeout(self.frame_to_send.frame_time)

        was_sent = self.check_for_collision()

        if was_sent:
            yield self.env.timeout(self.times.get_ack_frame_time())
        else:
            yield self.env.timeout(Times.ack_timeout)
        return was_sent

    def interrupt_backoff_stations(self):
        for station in self.channel.wifi_stations_in_backoff:
            if station.process and station.process.is_alive:
                station.process.interrupt()
        for nru_node in self.channel.nru_nodes_in_backoff:
            if nru_node.process and nru_node.process.is_alive:
                nru_node.process.interrupt()

    def clear_transmission_state(self, res):
        self.channel.active_wifi_transmitters.clear()
        self.channel.active_nru_transmitters.clear()
        self.channel.tx_queue.release(res)

    def check_for_collision(self):
        total_transmitters = len(self.channel.active_wifi_transmitters) + len(self.channel.active_nru_transmitters)
        if total_transmitters != 1:
            self.sent_failed()
            return False
        else:
            self.sent_completed()
            return True

    def calculate_backoff_slots(self, failed_transmissions_in_row):
        upper_limit = (pow(2, failed_transmissions_in_row) * (self.min_cw + 1) - 1)
        upper_limit = min(upper_limit, self.max_cw)
        back_off = random.randint(0, upper_limit)
        self.channel.backoff_counts[back_off][self.channel.num_wifi_stations] += 1
        return back_off * self.times.t_slot

    def generate_wifi_frame(self):
        return WiFiDataPacket(5400, self.name, self.log_color, self.config.data_size, self.env.now)

    def sent_failed(self):
        log_transmission_event(self, "There was a collision")
        self.frame_to_send.number_of_retransmissions += 1
        self.channel.failed_transmissions += 1
        self.failed_transmissions += 1
        self.failed_transmissions_in_row += 1

        if self.frame_to_send.number_of_retransmissions > self.config.r_limit:
            self.frame_to_send = self.generate_wifi_frame()
            self.failed_transmissions_in_row = 0

    def sent_completed(self):
        log_transmission_event(self, f"Successfully sent frame, waiting ack: {self.times.get_ack_frame_time()}")
        self.frame_to_send.end_time_us = self.env.now
        self.frame_to_send.transmission_duration_us = (
                    self.frame_to_send.end_time_us - self.frame_to_send.start_time_us)
        self.channel.succeeded_transmissions += 1
        self.succeeded_transmissions += 1
        self.failed_transmissions_in_row = 0
        self.channel.bytes_sent += self.frame_to_send.data_size
        self.channel.data_airtime[self.name] += self.frame_to_send.frame_time
        return True

class NRUBaseStation:
    def __init__(self, env, name, channel, config_nr=NRUConfig()):
        self.config_nr = config_nr
        self.name = name
        self.env = env
        self.log_color = random.choice(LOG_COLORS)
        self.transmission_to_send = None
        self.succeeded_transmissions = 0
        self.failed_transmissions = 0
        self.failed_transmissions_in_row = 0
        self.min_cw = config_nr.min_cw
        self.N = None
        self.desync = 0
        self.next_sync_slot_boundry = 0
        self.max_cw = config_nr.max_cw
        self.channel = channel
        self.process = None
        self.first_interrupt = False
        self.back_off_time = 0
        self.time_to_next_sync_slot = 0
        self.waiting_backoff = False
        self.start_nr = 0

        self.channel.airtime_data_NR.update({name: 0})
        self.channel.airtime_control_NR.update({name: 0})

        env.process(self.start_process())
        env.process(self.sync_slot_counter())

    def start_process(self):
        while True:
            was_sent = False
            while not was_sent:
                if GAP_MODE_ENABLED:
                    self.process = self.env.process(self.wait_back_off_gap())
                else:
                    self.process = self.env.process(self.wait_back_off())
                yield self.process
                was_sent = yield self.env.process(self.send_transmission())

    def wait_back_off_gap(self):
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)
        prioritization_period_time = self.config_nr.prioritization_period_us + self.config_nr.M * self.config_nr.observation_slot_duration
        self.back_off_time += prioritization_period_time

        while self.back_off_time > -1:
            try:
                with self.channel.tx_lock.request() as req:
                    yield req

                self.time_to_next_sync_slot = self.next_sync_slot_boundry - self.env.now

                # Adjust for sync slots
                while self.back_off_time >= self.time_to_next_sync_slot:
                    self.time_to_next_sync_slot += self.config_nr.synchronization_slot_duration

                gap_time = self.time_to_next_sync_slot - self.back_off_time
                yield self.env.timeout(gap_time)

                self.first_interrupt = True
                self.start_nr = self.env.now

                # Check channel state
                if len(self.channel.active_nru_transmitters) + len(self.channel.active_wifi_transmitters) > 0:
                    with self.channel.tx_lock.request() as req:
                        yield req
                else:
                    log_transmission_event(self, f"Starting to wait backoff: ({self.back_off_time}) us...")
                    self.channel.nru_nodes_in_backoff.append(self)
                    self.waiting_backoff = True

                    yield self.env.timeout(self.back_off_time)
                    log_transmission_event(self, f"Backoff waited, sending frame...")
                    self.back_off_time = -1
                    self.waiting_backoff = False
                    self.channel.nru_nodes_in_backoff.remove(self)

            except simpy.Interrupt:
                if self.first_interrupt and self.start_nr is not None and self.waiting_backoff:
                    log_transmission_event(self, "Backoff was interrupted, waiting to resume backoff...")
                    already_waited = self.env.now - self.start_nr

                    if already_waited <= prioritization_period_time:
                        self.back_off_time -= prioritization_period_time
                    else:
                        slots_waited = int(
                            (already_waited - prioritization_period_time) / self.config_nr.observation_slot_duration)
                        self.back_off_time -= ((
                                                           slots_waited * self.config_nr.observation_slot_duration) + prioritization_period_time)

                    self.back_off_time += prioritization_period_time
                    self.first_interrupt = False
                    self.waiting_backoff = False

    def wait_back_off(self):
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)
        prioritization_period_time = self.config_nr.prioritization_period_us + self.config_nr.M * self.config_nr.observation_slot_duration

        while self.back_off_time > -1:
            try:
                with self.channel.tx_lock.request() as req:
                    yield req

                self.first_interrupt = True
                self.back_off_time += prioritization_period_time
                log_transmission_event(self, f"Starting to wait backoff (with PP): ({self.back_off_time}) us...")
                start = self.env.now
                self.channel.nru_nodes_in_backoff.append(self)

                yield self.env.timeout(self.back_off_time)
                log_transmission_event(self, f"Backoff waited, sending frame...")
                self.back_off_time = -1
                self.channel.nru_nodes_in_backoff.remove(self)

            except simpy.Interrupt:
                if self.first_interrupt and start is not None:
                    already_waited = self.env.now - start
                    if already_waited <= prioritization_period_time:
                        self.back_off_time -= prioritization_period_time
                    else:
                        slots_waited = int(
                            (already_waited - prioritization_period_time) / self.config_nr.observation_slot_duration)
                        self.back_off_time -= ((
                                                           slots_waited * self.config_nr.observation_slot_duration) + prioritization_period_time)
                    self.first_interrupt = False

    def sync_slot_counter(self):
        self.desync = random.randint(self.config_nr.min_sync_slot_desync, self.config_nr.max_sync_slot_desync)
        self.next_sync_slot_boundry = self.desync
        yield self.env.timeout(self.desync)
        while True:
            self.next_sync_slot_boundry += self.config_nr.synchronization_slot_duration
            yield self.env.timeout(self.config_nr.synchronization_slot_duration)

    def send_transmission(self):
        self.channel.active_nru_transmitters.append(self)
        self.transmission_to_send = self.create_nru_transmission()
        res = self.channel.tx_queue.request(
            priority=(MAX_TRANSMISSION_PRIORITY - self.transmission_to_send.transmission_time))

        try:
            result = yield res | self.env.timeout(0)
            if res not in result:
                raise simpy.Interrupt("There is a longer frame...")

            with self.channel.tx_lock.request() as lock:
                yield lock

                # Interrupt backoff stations
                for station in self.channel.wifi_stations_in_backoff:
                    if station.process and station.process.is_alive:
                        station.process.interrupt()
                for nru_node in self.channel.nru_nodes_in_backoff:
                    if nru_node.process and nru_node.process.is_alive:
                        nru_node.process.interrupt()

                yield self.env.timeout(self.transmission_to_send.transmission_time)
                self.channel.nru_nodes_in_backoff.clear()

                was_sent = self.check_for_collision()

                if was_sent:
                    self.channel.airtime_control_NR[self.name] += self.transmission_to_send.rs_time
                    self.channel.airtime_data_NR[self.name] += self.transmission_to_send.airtime
                    self.clear_transmission_state(res)
                    return True

                self.clear_transmission_state(res)
                self.channel.tx_queue = simpy.PreemptiveResource(self.env, capacity=1)
                return False

        except simpy.Interrupt:
            yield self.env.timeout(self.transmission_to_send.transmission_time)

        return self.check_for_collision()

    def clear_transmission_state(self, res):
        self.channel.active_nru_transmitters.clear()
        self.channel.active_wifi_transmitters.clear()
        self.channel.tx_queue.release(res)

    def check_for_collision(self):
        total_transmitters = len(self.channel.active_wifi_transmitters) + len(self.channel.active_nru_transmitters)
        if total_transmitters != 1:
            self.sent_failed()
            return False
        else:
            self.sent_completed()
            return True

    def create_nru_transmission(self):
        transmission_time = self.config_nr.mcot * 1000
        rs_time = 0 if GAP_MODE_ENABLED else (self.next_sync_slot_boundry - self.env.now)
        airtime = transmission_time - rs_time
        return NRUTransmission(transmission_time, self.name, self.log_color, self.env.now, airtime, rs_time)

    def calculate_backoff_slots(self, failed_transmissions_in_row):
        upper_limit = (pow(2, failed_transmissions_in_row) * (self.min_cw + 1) - 1)
        upper_limit = min(upper_limit, self.max_cw)
        back_off = random.randint(0, upper_limit)
        self.channel.backoff_counts[back_off][self.channel.num_wifi_stations] += 1
        return back_off * self.config_nr.observation_slot_duration

    def sent_failed(self):
        log_transmission_event(self, "There was a collision")
        self.transmission_to_send.number_of_retransmissions += 1
        self.channel.failed_transmissions_NR += 1
        self.failed_transmissions += 1
        self.failed_transmissions_in_row += 1

        if self.transmission_to_send.number_of_retransmissions > 7:
            self.failed_transmissions_in_row = 0

    def sent_completed(self):
        log_transmission_event(self, f"Successfully sent transmission")
        self.transmission_to_send.end_time_us = self.env.now
        self.transmission_to_send.transmission_duration_us = (
                    self.transmission_to_send.end_time_us - self.transmission_to_send.start_time_us)
        self.channel.succeeded_transmissions_NR += 1
        self.succeeded_transmissions += 1
        self.failed_transmissions_in_row = 0
        return True

def simulate_coexistence(
        number_of_stations: int,
        number_of_gnb: int,
        seed: int,
        simulation_time: int,
        config: WiFiConfig,
        configNr: NRUConfig,
        backoff_counts: Dict[int, Dict[int, int]],
        data_airtime: Dict[str, int],
        control_airtime: Dict[str, int],
        airtime_data_NR: Dict[str, int],
        airtime_control_NR: Dict[str, int],
        nru_mode: str,
        output_path: str
):
    global GAP_MODE_ENABLED
    GAP_MODE_ENABLED = (nru_mode.lower() == "gap")
    random.seed(seed)
    environment = simpy.Environment()


    channel = WirelessMedium(
        simpy.PreemptiveResource(environment, capacity=1),
        simpy.Resource(environment, capacity=1),
        number_of_stations,
        number_of_gnb,
        backoff_counts,
        data_airtime,
        control_airtime,
        airtime_data_NR,
        airtime_control_NR
    )

    for i in range(1, number_of_stations + 1):
        # WiFiStation(environment, f"WiFiStation {i}", channel, config)
        WiFiStation(environment, f"WiFiStation {i}", channel, config)

    for i in range(1, number_of_gnb + 1):
        NRUBaseStation(environment, f"NRUBaseStation {i}", channel, configNr)

    environment.run(until=simulation_time * 1000000)

    # Calculate statistics
    p_coll = 0
    if number_of_stations > 0 and (channel.failed_transmissions + channel.succeeded_transmissions) > 0:
        p_coll = "{:.4f}".format(
            channel.failed_transmissions / (channel.failed_transmissions + channel.succeeded_transmissions))

    p_coll_NR = 0
    if number_of_gnb > 0 and (channel.failed_transmissions_NR + channel.succeeded_transmissions_NR) > 0:
        p_coll_NR = "{:.4f}".format(
            channel.failed_transmissions_NR / (channel.failed_transmissions_NR + channel.succeeded_transmissions_NR))

    # Calculate channel metrics
    channel_occupancy_time = 0
    channel_efficiency = 0
    for i in range(1, number_of_stations + 1):
        station_key = f"WiFiStation {i}"
        if station_key in channel.data_airtime and station_key in channel.control_airtime:
            channel_occupancy_time += channel.data_airtime[station_key] + channel.control_airtime[station_key]
            channel_efficiency += channel.data_airtime[station_key]

    channel_occupancy_time_NR = 0
    channel_efficiency_NR = 0
    for i in range(1, number_of_gnb + 1):
        gnb_key = f"NRUBaseStation {i}"
        if gnb_key in channel.airtime_data_NR and gnb_key in channel.airtime_control_NR:
            channel_occupancy_time_NR += channel.airtime_data_NR[gnb_key] + channel.airtime_control_NR[gnb_key]
            channel_efficiency_NR += channel.airtime_data_NR[gnb_key]

    time = simulation_time * 1000000

    # Normalize metrics
    normalized_channel_occupancy_time = channel_occupancy_time / time
    normalized_channel_efficiency = channel_efficiency / time
    normalized_channel_occupancy_time_NR = channel_occupancy_time_NR / time
    normalized_channel_efficiency_NR = channel_efficiency_NR / time
    normalized_channel_occupancy_time_all = (channel_occupancy_time + channel_occupancy_time_NR) / time
    normalized_channel_efficiency_all = (channel_efficiency + channel_efficiency_NR) / time

    # Calculate fairness metrics
    fairness = (normalized_channel_occupancy_time_all ** 2) / (2 *
                                                               (normalized_channel_occupancy_time ** 2 + normalized_channel_occupancy_time_NR ** 2))
    joint = fairness * normalized_channel_occupancy_time_all

    # Output summary
    print(
        f"SEED = {seed} WiFi AP's:={number_of_stations} NR GNB's:={number_of_gnb}  CW_MIN = {config.min_cw} CW_MAX = {config.max_cw} "
        f"WiFi Pcol:={p_coll} WiFi Cot:={normalized_channel_occupancy_time} WiFi Eff:={normalized_channel_efficiency} "
        f"GNB Pcol:={p_coll_NR} GNB Cot:={normalized_channel_occupancy_time_NR} GNB Eff:={normalized_channel_efficiency_NR} "
        f" All Cot:={normalized_channel_occupancy_time_all} All Eff:={normalized_channel_efficiency_all}"
    )
    print(f"WiFi Successful: {channel.succeeded_transmissions} Fail: {channel.failed_transmissions}")
    print(f"NR-U Successful: {channel.succeeded_transmissions_NR} Fail: {channel.failed_transmissions_NR}")
    print(f'Jain\'s Fairness Index: {fairness:.4f}')
    print(f'Joint Airtime Fairness: {joint:.4f}')

    # Write results to output file
    write_header = not os.path.isfile(output_path)
    with open(output_path, mode='a', newline="") as result_file:
        result_adder = csv.writer(result_file)

        if write_header:
            result_adder.writerow([
                "simulation_seed", "wifi_node_count", "nru_node_count",
                "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
                "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
                "total_channel_occupancy", "total_network_efficiency"
            ])

        result_adder.writerow([
            seed,
            number_of_stations,
            number_of_gnb,
            normalized_channel_occupancy_time,
            normalized_channel_efficiency,
            p_coll,
            normalized_channel_occupancy_time_NR,
            normalized_channel_efficiency_NR,
            p_coll_NR,
            normalized_channel_occupancy_time_all,
            normalized_channel_efficiency_all
        ])