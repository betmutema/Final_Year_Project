import logging
import csv
import os
import random
import simpy
from dataclasses import dataclass, field
from typing import Dict, List
from .radio_parameters import Times

# --------------------------
# Configuration and Constants
# --------------------------
MAX_TRANSMISSION_PRIORITY = 100000  # Used to prioritize shorter transmissions via preemptive resource

# Configure minimal logging (only critical errors)
logging.basicConfig(format='%(asctime)s %(message)s', filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

# ANSI colors for node-specific logging
LOG_COLORS = ["\033[32m", "\033[31m", "\033[33m", "\033[34m", "\033[35m", "\033[36m", "\033[37m"]

# --------------------------
# Custom Exceptions
# --------------------------
class ChannelBusyError(Exception):
    pass

# --------------------------
# Configuration Dataclasses
# --------------------------
@dataclass()
class WiFiConfig:
    """Stores Wi-Fi node configuration parameters"""
    data_size: int = 1472   # MAC payload size (bytes)
    min_cw: int = 15        # Minimum contention window
    max_cw: int = 63        # Maximum contention window
    r_limit: int = 7        # Retry limit
    mcs: int = 7            # Modulation and Coding Scheme index

@dataclass()
class NRUConfig:
    prioritization_period_us: int = 16          # Prioritization period duration
    observation_slot_duration: int = 9          # Observation slot duration
    synchronization_slot_duration: int = 1000   # Sync slot duration
    max_sync_slot_desync: int = 1000            # Max sync randomization offset
    min_sync_slot_desync: int = 0               # Min sync randomization offset
    M: int = 3                                  # Number of observation slots
    min_cw: int = 15                            # Minimum contention window
    max_cw: int = 63                            # Maximum contention window
    mcot: int = 6                               # Max Channel Occupancy Time

def log_transmission_event(node, mes: str) -> None:
    """Logs transmission events with color coding by node

    Creates a formatted log message with timestamp, node identification,
    and the message, with color coding to help visually differentiate
    between different stations when reading the log.

    Args:
        node: The node (WiFi station or NR-U base station) generating the log
        mes: The message to log
    """
    logger.info(f"{node.log_color}Time: {node.env.now} Station: {node.name} Message: {mes}")

def generate_desync_offsets(max, number, min_distance=0):
    """Generates random desynchronization offsets with minimum spacing

    Creates a set of random offsets for NR-U stations to desynchronize
    their transmission timing while maintaining minimum separation.

    Args:
        max: Maximum allowable offset value
        number: Number of offset values to generate
        min_distance: Minimum distance between generated offsets

    Returns:
        List[int]: List of desynchronization offset values
    """
    # Generate initial random samples in the available range
    samples = random.sample(range(max - (number - 1) * (min_distance - 1)), number)
    # Compute indices that would sort the samples
    indices = sorted(range(len(samples)), key=lambda i: samples[i])
    # Compute ranks of the samples
    ranks = sorted(indices, key=lambda i: indices[i])
    # Add spacing between samples proportional to their rank
    return [sample + (min_distance - 1) * rank for sample, rank in zip(samples, ranks)]


@dataclass()
class WiFiDataPacket:
    """Represents a Wi-Fi data packet with transmission information

    Tracks all relevant information about a Wi-Fi packet transmission,
    including timing, size, source, and statistics about retransmissions.
    This information is used for calculating airtime usage and efficiency metrics.
    """
    frame_time: int  # Time to transmit the frame (microseconds)
    station_name: str  # Source station name
    log_color: str  # Color for logging
    data_size: int  # Size of data payload (bytes)
    start_time_us: int  # Transmission start time (simulation microseconds)
    number_of_retransmissions: int = 0  # Number of retransmission attempts
    end_time_us: int = None  # Transmission end time (simulation microseconds)
    transmission_duration_us: int = None  # Total transmission duration (microseconds)


@dataclass()
class NRUTransmission:
    """Represents an NR-U transmission with associated metadata

    Tracks all relevant information about an NR-U transmission,
    including timing, source, and statistics about the transmission success.
    This information is used for calculating airtime usage and efficiency metrics.

    NR-U transmissions consist of a reservation signal component and a data component,
    which are tracked separately to evaluate effective spectrum utilization.
    """
    transmission_time: int  # Total transmission time (microseconds)
    enb_name: str  # Source node name
    log_color: str  # Color for logging
    start_time_us: int  # Transmission start time (simulation microseconds)
    airtime: int  # Effective airtime usage for data (microseconds)
    rs_time: int  # Reservation signal time (microseconds)
    number_of_retransmissions: int = 0  # Number of retransmission attempts
    end_time_us: int = None  # Transmission end time (simulation microseconds)
    transmission_duration_us: int = None  # Total transmission duration (microseconds)
    collided: bool = False  # Collision flag

# --------------------------
# Core Simulation Components
# --------------------------
@dataclass()
class WirelessMedium:
    """Represents the shared wireless medium for the coexistence simulation

    This class is the central component of the simulation, tracking the state
    of the wireless channel, managing access to the shared medium, and collecting
    statistics about transmissions from both Wi-Fi and NR-U nodes.

    The medium uses two types of resources:
    1. tx_queue: A preemptive resource that prioritizes transmissions by duration
    2. tx_lock: A standard resource that controls channel access during backoff

    It maintains detailed statistics about channel usage, collisions, and transmission
    effectiveness for both technologies to evaluate coexistence performance.
    """
    tx_queue: simpy.PreemptiveResource  # Prioritized transmission queue
    tx_lock: simpy.Resource  # Channel access lock
    num_wifi_stations: int  # Number of Wi-Fi stations
    num_nru_nodes: int  # Number of NR-U nodes
    backoff_counts: Dict[int, Dict[int, int]]  # Track backoff statistics
    data_airtime_WiFi: Dict[str, int]  # Wi-Fi data transmission airtime per station
    control_airtime_WiFi: Dict[str, int]  # Wi-Fi control signal airtime per station
    data_airtime_NR: Dict[str, int]  # NR-U data transmission airtime per node
    control_airtime_NR: Dict[str, int]  # NR-U control signal airtime per node
    active_wifi_transmitters: List = field(default_factory=list)  # Active Wi-Fi transmitters
    wifi_stations_in_backoff: List = field(default_factory=list)  # Wi-Fi stations in backoff
    active_nru_transmitters: List = field(default_factory=list)  # Active NR-U transmitters
    nru_nodes_in_backoff: List = field(default_factory=list)  # NR-U nodes in backoff
    failed_transmissions_WiFi: int = 0  # Failed Wi-Fi transmission count
    succeeded_transmissions_WiFi: int = 0  # Successful Wi-Fi transmission count
    bytes_sent: int = 0  # Total bytes successfully transmitted
    failed_transmissions_NR: int = 0  # Failed NR-U transmission count
    succeeded_transmissions_NR: int = 0  # Successful NR-U transmission count

class WiFiStation:
    """Simulates a Wi-Fi station with DCF channel access mechanism

    Implements the IEEE 802.11 Distributed Coordination Function (DCF)
    with exponential backoff for channel access.
    """

    def __init__(self, env, name, channel, config=WiFiConfig()):
        """Initialize a new Wi-Fi station

        Args:
            env: SimPy environment
            name: Station identifier
            channel: Shared wireless medium
            config: Wi-Fi configuration parameters
        """
        self.config = config
        self.times = Times(config.data_size, config.mcs)  # Calculate timing parameters
        self.name = name
        self.env = env
        self.log_color = random.choice(LOG_COLORS)  # Assign random color for logging
        self.frame_to_send = None
        self.succeeded_transmissions_WiFi = 0  # Successful transmission counter
        self.failed_transmissions_WiFi = 0  # Failed transmission counter
        self.failed_transmissions_in_row = 0  # Consecutive failures counter
        self.min_cw = config.min_cw  # Minimum contention window
        self.max_cw = config.max_cw  # Maximum contention window
        self.channel = channel  # Shared wireless medium
        self.process = None  # Current process reference
        self.first_interrupt = False  # Interrupt flag
        self.back_off_time = 0  # Current backoff time
        self.start = 0  # Backoff start time

        # Register station in channel statistics
        self.channel.data_airtime_WiFi.update({name: 0})
        self.channel.control_airtime_WiFi.update({name: 0})
        env.process(self.start_process())  # Start the station process

    def start_process(self):
        """Main station process - continuously generates and sends frames"""
        while True:
            self.frame_to_send = self.generate_wifi_frame()  # Generate a new frame
            was_sent = False
            while not was_sent:
                # Execute backoff procedure
                self.process = self.env.process(self.wait_back_off())
                yield self.process
                # Try to send the frame after backoff
                was_sent = yield self.env.process(self.send_frame())

    def wait_back_off(self):
        """Implements Wi-Fi exponential backoff procedure"""
        # Calculate backoff time based on current retry count
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)

        while self.back_off_time > -1:
            try:
                # Request channel access lock
                with self.channel.tx_lock.request() as req:
                    yield req

                # Add DIFS wait time to backoff
                self.back_off_time += Times.t_difs
                log_transmission_event(self, f"Starting to wait backoff (with DIFS): ({self.back_off_time})u...")
                self.first_interrupt = True
                self.start = self.env.now
                self.channel.wifi_stations_in_backoff.append(self)

                # Wait for backoff time
                yield self.env.timeout(self.back_off_time)
                log_transmission_event(self, f"Backoff waited, sending frame...")
                self.back_off_time = -1  # Backoff complete

                self.channel.wifi_stations_in_backoff.remove(self)

            except simpy.Interrupt:
                # Handle interruption (e.g., when channel becomes busy)
                if self.first_interrupt and self.start is not None:
                    log_transmission_event(self, "Waiting was interrupted, waiting to resume backoff...")
                    all_waited = self.env.now - self.start
                    # Calculate remaining backoff time
                    if all_waited <= Times.t_difs:
                        self.back_off_time -= Times.t_difs
                    else:
                        slot_waited = int((all_waited - Times.t_difs) / Times.t_slot)
                        self.back_off_time -= ((slot_waited * Times.t_slot) + Times.t_difs)
                    self.first_interrupt = False

    def send_frame(self):
        """Attempts to transmit a frame after backoff completion

        Returns:
            bool: True if transmission successful, False otherwise
        """
        # Register as active transmitter
        self.channel.active_wifi_transmitters.append(self)
        # Request transmission queue with priority based on frame duration
        res = self.channel.tx_queue.request(priority=(MAX_TRANSMISSION_PRIORITY - self.frame_to_send.frame_time))

        try:
            # Check if this transmission gets preempted
            result = yield res | self.env.timeout(0)
            if res not in result:
                raise simpy.Interrupt("There is a longer frame...")

            # Acquire channel lock
            with self.channel.tx_lock.request() as lock:
                yield lock

                # Interrupt other stations in backoff
                self.interrupt_backoff_stations()

                log_transmission_event(self, f'Starting sending frame: {self.frame_to_send.frame_time}')
                # Simulate frame transmission time
                yield self.env.timeout(self.frame_to_send.frame_time)
                self.channel.wifi_stations_in_backoff.clear()

                # Check if transmission collided
                was_sent = self.check_for_collision()

                if was_sent:
                    # If successful, wait for ACK
                    self.channel.control_airtime_WiFi[self.name] += self.times.get_ack_frame_time()
                    yield self.env.timeout(self.times.get_ack_frame_time())
                    self.clear_transmission_state(res)
                    return True

                # If collision detected, clean up
                self.clear_transmission_state(res)
                self.channel.tx_queue = simpy.PreemptiveResource(self.env, capacity=1)
                yield self.env.timeout(self.times.ack_timeout)
                return False

        except simpy.Interrupt:
            # Handle preemption by waiting anyway (simulates collision)
            yield self.env.timeout(self.frame_to_send.frame_time)

        # Check transmission result
        was_sent = self.check_for_collision()

        if was_sent:
            # Successful transmission, wait for ACK
            yield self.env.timeout(self.times.get_ack_frame_time())
        else:
            # Failed transmission, wait for ACK timeout
            yield self.env.timeout(Times.ack_timeout)
        return was_sent

    def interrupt_backoff_stations(self):
        """Interrupts all stations in backoff state (channel became busy)"""
        for station in self.channel.wifi_stations_in_backoff:
            if station.process and station.process.is_alive:
                station.process.interrupt()
        for nru_node in self.channel.nru_nodes_in_backoff:
            if nru_node.process and nru_node.process.is_alive:
                nru_node.process.interrupt()

    def clear_transmission_state(self, res):
        """Cleans up state after transmission attempt"""
        self.channel.active_wifi_transmitters.clear()
        self.channel.active_nru_transmitters.clear()
        self.channel.tx_queue.release(res)

    def check_for_collision(self):
        """Determines if a collision occurred during transmission

        Returns:
            bool: True if no collision, False if collision detected
        """
        total_transmitters = len(self.channel.active_wifi_transmitters) + len(self.channel.active_nru_transmitters)
        if total_transmitters != 1:
            # More than one transmitting node means collision
            self.sent_failed()
            return False
        else:
            # Single transmitter means success
            self.sent_completed()
            return True

    def calculate_backoff_slots(self, failed_transmissions_in_row):
        """Calculates backoff slots using binary exponential backoff algorithm

        Args:
            failed_transmissions_in_row: Number of consecutive failed transmission attempts

        Returns:
            int: Calculated backoff time in microseconds
        """
        # Calculate contention window size using binary exponential backoff
        upper_limit = (pow(2, failed_transmissions_in_row) * (self.min_cw + 1) - 1)
        upper_limit = min(upper_limit, self.max_cw)  # Cap at max_cw
        back_off = random.randint(0, upper_limit)  # Select random slot
        # Update statistics
        self.channel.backoff_counts[back_off][self.channel.num_wifi_stations] += 1
        return back_off * self.times.t_slot  # Convert slots to time

    def generate_wifi_frame(self):
        """Creates a new Wi-Fi data packet to transmit

        Returns:
            WiFiDataPacket: Newly created packet
        """
        return WiFiDataPacket(5400, self.name, self.log_color, self.config.data_size, self.env.now)

    def sent_failed(self):
        """Handles failed transmission (collision)"""
        log_transmission_event(self, "There was a collision")
        self.frame_to_send.number_of_retransmissions += 1
        self.channel.failed_transmissions_WiFi += 1
        self.failed_transmissions_WiFi += 1
        self.failed_transmissions_in_row += 1

        # If retransmission limit reached, drop frame and reset counter
        if self.frame_to_send.number_of_retransmissions > self.config.r_limit:
            self.frame_to_send = self.generate_wifi_frame()
            self.failed_transmissions_in_row = 0

    def sent_completed(self):
        """Handles successful transmission"""
        log_transmission_event(self, f"Successfully sent frame, waiting ack: {self.times.get_ack_frame_time()}")
        # Update packet statistics
        self.frame_to_send.end_time_us = self.env.now
        self.frame_to_send.transmission_duration_us = (
                    self.frame_to_send.end_time_us - self.frame_to_send.start_time_us)
        # Update channel statistics
        self.channel.succeeded_transmissions_WiFi += 1
        self.succeeded_transmissions_WiFi += 1
        self.failed_transmissions_in_row = 0
        self.channel.bytes_sent += self.frame_to_send.data_size
        self.channel.data_airtime_WiFi[self.name] += self.frame_to_send.frame_time
        return True


class NRUBaseStation:
    """Simulates an NR-U base station with LBT channel access

    Implements Listen-Before-Talk (LBT) with backoff for NR-U
    and accounts for synchronization slots.
    """

    def __init__(self, env, name, channel, config_nr=NRUConfig()):
        """Initialize a new NR-U base station

        Args:
            env: SimPy environment
            name: Station identifier
            channel: Shared wireless medium
            config_nr: NR-U configuration parameters
        """
        self.config_nr = config_nr
        self.name = name
        self.env = env
        self.log_color = random.choice(LOG_COLORS)
        self.transmission_to_send = None
        self.succeeded_transmissions = 0  # Successful transmission counter
        self.failed_transmissions = 0  # Failed transmission counter
        self.failed_transmissions_in_row = 0  # Consecutive failures counter
        self.min_cw = config_nr.min_cw  # Minimum contention window
        self.N = None
        self.desync = 0  # Desynchronization offset
        self.next_sync_slot_boundry = 0  # Next sync slot boundary time
        self.max_cw = config_nr.max_cw  # Maximum contention window
        self.channel = channel  # Shared wireless medium
        self.process = None  # Current process reference
        self.first_interrupt = False  # Interrupt flag
        self.back_off_time = 0  # Current backoff time
        self.time_to_next_sync_slot = 0  # Time until next sync slot
        self.waiting_backoff = False  # Backoff in progress flag
        self.start_nr = 0  # Backoff start time

        # Register station in channel statistics
        self.channel.data_airtime_NR.update({name: 0})
        self.channel.control_airtime_NR.update({name: 0})

        # Start main processes
        env.process(self.start_process())
        env.process(self.sync_slot_counter())  # Track synchronization slots

    def start_process(self):
        """Main station process - continuously sends transmissions"""
        while True:
            was_sent = False
            while not was_sent:
                # Execute backoff procedure based on mode
                if GAP_MODE_ENABLED:
                    self.process = self.env.process(self.wait_back_off_gap())
                else:
                    self.process = self.env.process(self.wait_back_off())
                yield self.process
                # Try to send after backoff completes
                was_sent = yield self.env.process(self.send_transmission())

    def wait_back_off_gap(self):
        """Implements gap-mode backoff procedure for NR-U

        In gap mode, NR-U stations avoid transmission during sync slots
        and implement a backoff mechanism between sync slots.
        """
        # Calculate backoff time
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)
        prioritization_period_time = self.config_nr.prioritization_period_us + self.config_nr.M * self.config_nr.observation_slot_duration
        self.back_off_time += prioritization_period_time

        while self.back_off_time > -1:
            try:
                # Request channel access
                with self.channel.tx_lock.request() as req:
                    yield req

                # Calculate time to next sync slot
                self.time_to_next_sync_slot = self.next_sync_slot_boundry - self.env.now

                # Adjust backoff to avoid transmission during sync slots
                while self.back_off_time >= self.time_to_next_sync_slot:
                    self.time_to_next_sync_slot += self.config_nr.synchronization_slot_duration

                # Wait until gap between sync slots
                gap_time = self.time_to_next_sync_slot - self.back_off_time
                yield self.env.timeout(gap_time)

                self.first_interrupt = True
                self.start_nr = self.env.now

                # Check channel state before proceeding
                if len(self.channel.active_nru_transmitters) + len(self.channel.active_wifi_transmitters) > 0:
                    # Channel busy, wait for it to become idle
                    with self.channel.tx_lock.request() as req:
                        yield req
                else:
                    # Channel idle, start backoff
                    log_transmission_event(self, f"Starting to wait backoff: ({self.back_off_time}) us...")
                    self.channel.nru_nodes_in_backoff.append(self)
                    self.waiting_backoff = True

                    # Wait for backoff time
                    yield self.env.timeout(self.back_off_time)
                    log_transmission_event(self, f"Backoff waited, sending frame...")
                    self.back_off_time = -1
                    self.waiting_backoff = False
                    self.channel.nru_nodes_in_backoff.remove(self)

            except simpy.Interrupt:
                # Handle interruption (e.g., when channel becomes busy)
                if self.first_interrupt and self.start_nr is not None and self.waiting_backoff:
                    log_transmission_event(self, "Backoff was interrupted, waiting to resume backoff...")
                    already_waited = self.env.now - self.start_nr

                    # Calculate remaining backoff time
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
        """Implements standard (reservation signal) backoff procedure for NR-U"""
        # Calculate backoff time
        self.back_off_time = self.calculate_backoff_slots(self.failed_transmissions_in_row)
        prioritization_period_time = self.config_nr.prioritization_period_us + self.config_nr.M * self.config_nr.observation_slot_duration

        while self.back_off_time > -1:
            try:
                # Request channel access
                with self.channel.tx_lock.request() as req:
                    yield req

                # Start backoff procedure
                self.first_interrupt = True
                self.back_off_time += prioritization_period_time
                log_transmission_event(self, f"Starting to wait backoff (with PP): ({self.back_off_time}) us...")
                start = self.env.now
                self.channel.nru_nodes_in_backoff.append(self)

                # Wait for backoff time
                yield self.env.timeout(self.back_off_time)
                log_transmission_event(self, f"Backoff waited, sending frame...")
                self.back_off_time = -1
                self.channel.nru_nodes_in_backoff.remove(self)

            except simpy.Interrupt:
                # Handle interruption (e.g., when channel becomes busy)
                if self.first_interrupt and start is not None:
                    already_waited = self.env.now - start
                    # Calculate remaining backoff time
                    if already_waited <= prioritization_period_time:
                        self.back_off_time -= prioritization_period_time
                    else:
                        slots_waited = int(
                            (already_waited - prioritization_period_time) / self.config_nr.observation_slot_duration)
                        self.back_off_time -= ((
                                                           slots_waited * self.config_nr.observation_slot_duration) + prioritization_period_time)
                    self.first_interrupt = False

    def sync_slot_counter(self):
        """Continuously tracks synchronization slot timing

        Maintains a counter for synchronization slots with a station-specific
        random offset (desynchronization) to prevent all stations from
        synchronizing at exactly the same time, which would increase collision probability.

        This process runs for the entire simulation duration and updates the
        next_sync_slot_boundry variable used for timing transmissions.
        """
        # Initialize with random desynchronization offset to prevent synchronization across stations
        self.desync = random.randint(self.config_nr.min_sync_slot_desync, self.config_nr.max_sync_slot_desync)
        self.next_sync_slot_boundry = self.desync
        yield self.env.timeout(self.desync)

        # Continuously track sync slot boundaries
        while True:
            self.next_sync_slot_boundry += self.config_nr.synchronization_slot_duration
            yield self.env.timeout(self.config_nr.synchronization_slot_duration)

    def send_transmission(self):
        """Attempts to transmit after backoff completion

        Returns:
            bool: True if transmission successful, False otherwise
        """
        # Register as active transmitter
        self.channel.active_nru_transmitters.append(self)
        self.transmission_to_send = self.create_nru_transmission()
        # Request transmission queue with priority based on transmission duration
        res = self.channel.tx_queue.request(
            priority=(MAX_TRANSMISSION_PRIORITY - self.transmission_to_send.transmission_time))

        try:
            # Check if this transmission gets preempted
            result = yield res | self.env.timeout(0)
            if res not in result:
                raise simpy.Interrupt("There is a longer frame...")

            # Acquire channel lock
            with self.channel.tx_lock.request() as lock:
                yield lock

                # Interrupt stations in backoff
                for station in self.channel.wifi_stations_in_backoff:
                    if station.process and station.process.is_alive:
                        station.process.interrupt()
                for nru_node in self.channel.nru_nodes_in_backoff:
                    if nru_node.process and nru_node.process.is_alive:
                        nru_node.process.interrupt()

                # Simulate transmission time
                yield self.env.timeout(self.transmission_to_send.transmission_time)
                self.channel.nru_nodes_in_backoff.clear()

                # Check for collision
                was_sent = self.check_for_collision()

                if was_sent:
                    # Update channel airtime statistics
                    self.channel.control_airtime_NR[self.name] += self.transmission_to_send.rs_time
                    self.channel.data_airtime_NR[self.name] += self.transmission_to_send.airtime
                    self.clear_transmission_state(res)
                    return True

                # Handle collision
                self.clear_transmission_state(res)
                self.channel.tx_queue = simpy.PreemptiveResource(self.env, capacity=1)
                return False

        except simpy.Interrupt:
            # Handle preemption (simulates collision)
            yield self.env.timeout(self.transmission_to_send.transmission_time)

        return self.check_for_collision()

    def clear_transmission_state(self, res):
        """Cleans up state after transmission attempt"""
        self.channel.active_nru_transmitters.clear()
        self.channel.active_wifi_transmitters.clear()
        self.channel.tx_queue.release(res)

    def check_for_collision(self):
        """Determines if a collision occurred during transmission

        Returns:
            bool: True if no collision, False if collision detected
        """
        total_transmitters = len(self.channel.active_wifi_transmitters) + len(self.channel.active_nru_transmitters)
        if total_transmitters != 1:
            # More than one transmitter means collision
            self.sent_failed()
            return False
        else:
            # Single transmitter means success
            self.sent_completed()
            return True

    def create_nru_transmission(self):
        """Creates a new NR-U transmission with appropriate timing parameters

        Calculates transmission parameters based on the current simulation state and
        NR-U configuration, including reservaton signal time and effective airtime.

        Returns:
            NRUTransmission: A new transmission object with calculated parameters
        """
        transmission_time = self.config_nr.mcot * 1000  # Convert max channel occupancy time from ms to μs
        # In gap mode, no reservation signal is used
        # Otherwise, calculate reservation signal time based on next sync slot
        rs_time = 0 if GAP_MODE_ENABLED else (self.next_sync_slot_boundry - self.env.now)
        # Effective airtime is total transmission time minus reservation signal time
        airtime = transmission_time - rs_time
        return NRUTransmission(transmission_time, self.name, self.log_color, self.env.now, airtime, rs_time)

    def calculate_backoff_slots(self, failed_transmissions_in_row):
        """Calculates backoff slots using exponential backoff algorithm

        Args:
            failed_transmissions_in_row: Number of consecutive failed attempts

        Returns:
            int: Calculated backoff time in observation slots
        """
        # Calculate contention window size using binary exponential backoff
        upper_limit = (pow(2, failed_transmissions_in_row) * (self.min_cw + 1) - 1)
        upper_limit = min(upper_limit, self.max_cw)  # Cap at max_cw
        back_off = random.randint(0, upper_limit)  # Select random slot
        # Update statistics
        self.channel.backoff_counts[back_off][self.channel.num_wifi_stations] += 1
        return back_off * self.config_nr.observation_slot_duration  # Convert slots to time

    def sent_failed(self):
        """Handles failed transmission (collision)"""
        log_transmission_event(self, "There was a collision")
        self.transmission_to_send.number_of_retransmissions += 1
        self.channel.failed_transmissions_NR += 1
        self.failed_transmissions += 1
        self.failed_transmissions_in_row += 1

        if self.transmission_to_send.number_of_retransmissions > 7:
            self.failed_transmissions_in_row = 0

    def sent_completed(self):
        """Handles successful NR-U transmission

        Updates transmission statistics and resets failure counters
        after a successful transmission.

        Returns:
            bool: Always returns True to indicate successful transmission
        """
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
        number_of_gnbs: int,
        seed: int,
        simulation_time: int,
        config: WiFiConfig,
        configNr: NRUConfig,
        backoff_counts: Dict[int, Dict[int, int]],
        data_airtime_WiFi: Dict[str, int],
        control_airtime_WiFi: Dict[str, int],
        data_airtime_NR: Dict[str, int],
        control_airtime_NR: Dict[str, int],
        nru_mode: str,
        output_path: str
):
    """Main simulation function for WiFi and NR-U coexistence

    Sets up and runs the coexistence simulation with specified parameters,
    then calculates and outputs performance metrics.

    Args:
        number_of_stations: Number of WiFi stations
        number_of_gnbs: Number of NR-U base stations
        seed: Random seed for reproducibility
        simulation_time: Duration of simulation in seconds
        config: WiFi configuration parameters
        configNr: NR-U configuration parameters
        backoff_counts: Dictionary to track backoff statistics
        data_airtime_WiFi: Dictionary to track WiFi data transmission airtime
        control_airtime_WiFi: Dictionary to track WiFi control signal airtime
        data_airtime_NR: Dictionary to track NR-U data transmission airtime
        control_airtime_NR: Dictionary to track NR-U control signal airtime
        nru_mode: NR-U operating mode ("gap" or other)
        output_path: Path to output CSV file for results
    """

    # --------------------------
    # Global Variables
    # --------------------------
    # Controls whether NR-U operates in gap mode (True) or reservation signal mode (False)
    # Gap mode: NR-U transmissions avoid synchronization slots entirely
    # Reservation signal mode: NR-U uses reservation signals to hold the medium during sync slots
    global GAP_MODE_ENABLED # Default value, will be set by simulate_coexistence
    GAP_MODE_ENABLED = (nru_mode.lower() == "gap")
    random.seed(seed)
    environment = simpy.Environment()

    channel = WirelessMedium(
        simpy.PreemptiveResource(environment, capacity=1),
        simpy.Resource(environment, capacity=1),
        number_of_stations,
        number_of_gnbs,
        backoff_counts,
        data_airtime_WiFi,
        control_airtime_WiFi,
        data_airtime_NR,
        control_airtime_NR
    )

    for i in range(1, number_of_stations + 1):
        # Create WiFi stations and add them to the simulation environment
        WiFiStation(environment, f"WiFiStation {i}", channel, config)

    for i in range(1, number_of_gnbs + 1):
        # Create NR-U base stations and add them to the simulation environment
        NRUBaseStation(environment, f"NRUBaseStation {i}", channel, configNr)

    # Run the simulation for the specified duration (converted to microseconds)
    environment.run(until=simulation_time * 1000000)

    # Calculate collision probability statistics
    p_coll_WiFi = 0
    if number_of_stations > 0 and (channel.failed_transmissions_WiFi + channel.succeeded_transmissions_WiFi) > 0:
        p_coll_WiFi = "{:.4f}".format(
            channel.failed_transmissions_WiFi / (
                        channel.failed_transmissions_WiFi + channel.succeeded_transmissions_WiFi))

    p_coll_NR = 0
    if number_of_gnbs > 0 and (channel.failed_transmissions_NR + channel.succeeded_transmissions_NR) > 0:
        p_coll_NR = "{:.4f}".format(
            channel.failed_transmissions_NR / (channel.failed_transmissions_NR + channel.succeeded_transmissions_NR))

    # Calculate channel occupancy time and efficiency metrics for WiFi
    channel_occupancy_time_WiFi = 0
    channel_efficiency_WiFi = 0
    for i in range(1, number_of_stations + 1):
        station_key = f"WiFiStation {i}"
        if station_key in channel.data_airtime_WiFi and station_key in channel.control_airtime_WiFi:
            # Total airtime is data + control signals
            channel_occupancy_time_WiFi += channel.data_airtime_WiFi[station_key] + channel.control_airtime_WiFi[
                station_key]
            # Efficiency considers only data transmission time
            channel_efficiency_WiFi += channel.data_airtime_WiFi[station_key]

    # Calculate channel occupancy time and efficiency metrics for NR-U
    channel_occupancy_time_NR = 0
    channel_efficiency_NR = 0
    for i in range(1, number_of_gnbs + 1):
        gnb_key = f"NRUBaseStation {i}"
        if gnb_key in channel.data_airtime_NR and gnb_key in channel.control_airtime_NR:
            # Total airtime is data + control signals
            channel_occupancy_time_NR += channel.data_airtime_NR[gnb_key] + channel.control_airtime_NR[gnb_key]
            # Efficiency considers only data transmission time
            channel_efficiency_NR += channel.data_airtime_NR[gnb_key]

    # Total simulation time in microseconds
    time = simulation_time * 1000000

    # Normalize metrics to simulation time
    normalized_channel_occupancy_time_WiFi = channel_occupancy_time_WiFi / time
    normalized_channel_efficiency_WiFi = channel_efficiency_WiFi / time
    normalized_channel_occupancy_time_NR = channel_occupancy_time_NR / time
    normalized_channel_efficiency_NR = channel_efficiency_NR / time
    normalized_channel_occupancy_time_all = (channel_occupancy_time_WiFi + channel_occupancy_time_NR) / time
    normalized_channel_efficiency_all = (channel_efficiency_WiFi + channel_efficiency_NR) / time

    # Calculate fairness metrics using Jain's fairness index
    fairness = (normalized_channel_occupancy_time_all ** 2) / (2 *
                                                               (normalized_channel_occupancy_time_WiFi ** 2 + normalized_channel_occupancy_time_NR ** 2))
    # Calculate joint airtime fairness (product of fairness and total occupancy)
    joint = fairness * normalized_channel_occupancy_time_all

    # Output summary results to console
    print(
        f"seed = {seed} wifi_aps:= {number_of_stations} nru_gnbs:= {number_of_gnbs} cw_min = {config.min_cw} cw_max = {config.max_cw}"
        f" wifi_collision:= {p_coll_WiFi} wifi_occupancy:= {normalized_channel_occupancy_time_WiFi} wifi_efficiency:= {normalized_channel_efficiency_WiFi}"
        f" nru_collision:= {p_coll_NR} nru_occupancy:= {normalized_channel_occupancy_time_NR} nru_efficiency:= {normalized_channel_efficiency_NR}"
        f" total_occupancy:= {normalized_channel_occupancy_time_all} total_efficiency:= {normalized_channel_efficiency_all}"
    )
    print(f"wifi_suc: {channel.succeeded_transmissions_WiFi} wifi_fail: {channel.failed_transmissions_WiFi}")
    print(f"nru_succ: {channel.succeeded_transmissions_NR} nru_succ: {channel.failed_transmissions_NR}")
    print(f'jain_fairness: {fairness:.4f}')
    print(f'airtime_fairness: {joint:.4f}')

    # Write results to output CSV file
    write_header = not os.path.isfile(output_path)
    with open(output_path, mode='a', newline="") as result_file:
        result_adder = csv.writer(result_file)

        # Write header row if the file is new
        if write_header:
            result_adder.writerow([
                "simulation_seed", "wifi_node_count", "nru_node_count",
                "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
                "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
                "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index",
                "joint_airtime_fairness"
            ])

        # Write simulation results row
        result_adder.writerow([
            seed,
            number_of_stations,
            number_of_gnbs,
            normalized_channel_occupancy_time_WiFi,
            normalized_channel_efficiency_WiFi,
            p_coll_WiFi,
            normalized_channel_occupancy_time_NR,
            normalized_channel_efficiency_NR,
            p_coll_NR,
            normalized_channel_occupancy_time_all,
            normalized_channel_efficiency_all,
            fairness,
            joint
        ])