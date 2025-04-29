import math

MCS = {
    0: [6, 6],
    1: [9, 6],
    2: [12, 12],
    3: [18, 12],
    4: [24, 24],
    5: [36, 24],
    6: [48, 24],
    7: [54, 24],
}

class Times:
    # Time constants in microseconds
    t_slot = 9   # [us]
    t_sifs = 16  # [us]
    t_difs = 3 * t_slot + t_sifs     # [us]
    ack_timeout = 45    # [us]

    # Size constants in bits
    mac_overhead = 40 * 8   # [b] # Mac overhead
    ack_size = 14 * 8   # [b] # ACK size
    _overhead = 22   # [b] # overhead

    def __init__(self, payload: int = 1472, mcs: int = 7):
        self.payload = payload
        self.mcs = mcs
        # Using direct bit rates instead of Mb/us conversion
        self.data_rate = MCS[mcs][0]  # [b/us]
        self.ctr_rate = MCS[mcs][1]  # [b/us]

        # OFDM parameters
        self.ofdm_preamble = 16  # [us]
        self.ofdm_signal = 24 / self.ctr_rate  # [us]

    def get_ppdu_frame_time(self):
        msdu = self.payload * 8  # [b]
        mac_frame = Times.mac_overhead + msdu  # [b]

        # PPDU Padding calculation
        n_data = 4 * self.data_rate  # [b/symbol]
        ppdu_padding = math.ceil((Times._overhead + mac_frame) / n_data) * n_data - (Times._overhead + mac_frame)

        # CPSDU Frame
        cpsdu = Times._overhead + mac_frame + ppdu_padding  # [b]

        # PPDU Frame time calculation
        ppdu = self.ofdm_preamble + self.ofdm_signal + cpsdu / self.data_rate  # [us]
        return math.ceil(ppdu)  # [us]

    # ACK frame time with SIFS
    def get_ack_frame_time(self):
        # Use the optimized constant value directly
        ack = Times._overhead + Times.ack_size  # [b]
        ack = self.ofdm_preamble + self.ofdm_signal + ack / self.ctr_rate  # [us]
        ack_tx_time = Times.t_sifs + ack
        # return math.ceil(ack_tx_time)  # [us]
        return 44  # [us]

    # # ACK Timeout
    # def get_thr(self):
          # Calculate throughput in bits per microsecond
     #   return (self.payload * 8) / (self.get_ppdu_frame_time() + self.get_ack_frame_time() + Times.t_difs)