import numpy as np
import sounddevice as sd
import time
from scipy.signal import butter, lfilter, periodogram
import threading
import os
import matplotlib.pyplot as plt
from collections import deque

from send_commands import send_copy_command, send_paste_command

# SSH configuration
MAC_USER = "candyliu"
# MAC_IP = "172.20.10.9"
MAC_IP = "172.20.10.3"

class DopplerTracker:
    def __init__(self):
        # Audio parameters
        self.RATE = 44100        # Sample rate
        self.CHUNK = 2048        # Buffer size
        self.EMIT_FREQ = 18000   # Emitted frequency (Hz)
        self.CHANNELS = 1
        
        # Detection parameters
        self.MIN_AMPLITUDE = 1e-10  # Minimum amplitude for detection
        self.FREQ_RANGE = 200       # Search range around emitted frequency
        self.shift_threshold = 5    # Minimum shift for direction detection
        
        # History for simple filtering
        self.shift_history = [0] * 5
        self.last_direction = "none"
        self.consistent_count = 0
        
        # Flags and state
        self.running = False
        self.input_buffer = np.zeros(self.CHUNK, dtype=np.float32)
        self.buffer_ready = False
        
        self.shift_history_log = deque(maxlen=100)  # Stores (timestamp, avg_shift)
        self.plotting = True
        
        self.last_action_time = 0
        self.cooldown_sec = 10  # in seconds
        self.cooldown_active = False
        self.last_cooldown_print = 0
    
    def bandpass_filter(self, data, lowcut, highcut):
        """Apply a bandpass filter to isolate frequencies of interest"""
        nyquist = 0.5 * self.RATE
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(4, [low, high], btype='band')
        return lfilter(b, a, data)
    
    def save_plot(self, filename="doppler_shift_plot.png"):
        if len(self.shift_history_log) < 2:
            print("Not enough data to save plot.")
            return

        t0 = self.shift_history_log[0][0]
        x = [t - t0 for t, _ in self.shift_history_log]
        y = [shift for _, shift in self.shift_history_log]

        plt.figure(figsize=(10, 4))
        plt.plot(x, y, label="Doppler Shift (Hz)", lw=2)
        plt.xlabel("Time (s)")
        plt.ylabel("Frequency Shift (Hz)")
        plt.title("Hand Movement Tracking via Doppler Shift")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename)
        print(f"Plot saved as: {filename}")

    
    def live_plot(self):
        plt.ion()
        fig, ax = plt.subplots()
        line, = ax.plot([], [], lw=2)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency Shift (Hz)")
        ax.set_title("Live Hand Movement (Doppler Shift)")

        while self.plotting:
            if len(self.shift_history_log) >= 2:
                t0 = self.shift_history_log[0][0]
                x = [t - t0 for t, _ in self.shift_history_log]
                y = [shift for _, shift in self.shift_history_log]
                line.set_data(x, y)
                ax.set_xlim(max(0, x[-1] - 5), x[-1] + 0.1)  # 5-second rolling window
                ax.set_ylim(min(y) - 10, max(y) + 10)
                ax.figure.canvas.draw()
                ax.figure.canvas.flush_events()
            time.sleep(0.1)
        plt.close(fig)

    def audio_callback(self, indata, outdata, frames, time, status):
        # print(f"indata: {len(indata)}, input_buffer: {len(self.input_buffer)}")
        """This is called for each audio block"""
        if status:
            print(f"Audio status: {status}")
        
        # Copy input data to our buffer
        if len(indata) == len(self.input_buffer):
            self.input_buffer[:] = indata[:, 0]
            self.buffer_ready = True
        
        # Generate and output tone
        t = np.arange(frames) / self.RATE
        outdata[:, 0] = 0.1 * np.sin(2 * np.pi * self.EMIT_FREQ * t)
    
    def process_audio(self):
        """Process the recorded audio to detect Doppler shifts"""
        current_time = time.time()
        
        if (current_time - self.last_action_time) < self.cooldown_sec:
            self.cooldown_active = True
            if current_time - self.last_cooldown_print >= 1:
                remaining = int(self.cooldown_sec - (current_time - self.last_action_time))
                print(f"Cooldown active: {remaining} seconds left")
                self.last_cooldown_print = current_time
        else:
            self.cooldown_active = False
        
        # Make a copy of the buffer to avoid race conditions
        data = np.copy(self.input_buffer)
        
        # Apply bandpass filter to focus on frequencies of interest
        filtered_data = self.bandpass_filter(
            data, 
            self.EMIT_FREQ - self.FREQ_RANGE, 
            self.EMIT_FREQ + self.FREQ_RANGE
        )
        
        # Calculate power spectral density
        freq, psd = periodogram(filtered_data, self.RATE)
        
        # print(f"Max PSD in range: {np.max(psd)}, threshold: {self.MIN_AMPLITUDE}")
        
        # Find frequencies in our range of interest
        mask = (freq >= self.EMIT_FREQ - self.FREQ_RANGE) & (freq <= self.EMIT_FREQ + self.FREQ_RANGE)
        
        # If we have data in our frequency range
        if np.any(mask) and np.max(psd[mask]) > self.MIN_AMPLITUDE:
            # Find peak frequency
            peak_idx = np.argmax(psd[mask])
            peak_freq = freq[mask][peak_idx]
            peak_amplitude = np.sqrt(psd[mask][peak_idx])
            
            # Calculate frequency shift from emitted frequency
            freq_shift = peak_freq - self.EMIT_FREQ
            
            # Update shift history for smoothing
            self.shift_history.pop(0)
            self.shift_history.append(freq_shift)
            
            # Calculate average shift over history
            avg_shift = sum(self.shift_history) / len(self.shift_history)
            
            timestamp = time.time()
            self.shift_history_log.append((timestamp, avg_shift))
            
            # Determine direction based on frequency shift
            if abs(avg_shift) > self.shift_threshold:
                direction = "toward" if avg_shift > 0 else "away"
                
                # Check for consistent direction
                if direction == self.last_direction:
                    self.consistent_count += 1
                else:
                    self.consistent_count = 1
                    self.last_direction = direction
                
                # Only report if we have consistent readings
                if self.consistent_count == 3 and (current_time - self.last_action_time) >= self.cooldown_sec:
                    self.last_action_time = current_time  # Start cooldown
                    # Clear the terminal and print the current state
                    # os.system('clear' if os.name == 'posix' else 'cls')
                    if direction == "toward":
                        print("Detected consistent movement TOWARD — triggering paste (Cmd + V)")
                        send_paste_command(MAC_USER, MAC_IP)
                    elif direction == "away":
                        print("Detected consistent movement AWAY — triggering copy (Cmd + C)")
                        send_copy_command(MAC_USER, MAC_IP)
                    
            else:
                # Reset consistent count for no significant movement
                self.consistent_count = 0
                self.last_direction = "none"
    
    def start_stream(self):
        """Set up and start the audio stream"""
        sd.default.device = (2, 1) 
        
        self.stream = sd.Stream(
            samplerate=self.RATE,
            blocksize=self.CHUNK,
            channels=self.CHANNELS,
            dtype=np.float32,
            callback=self.audio_callback
        )
        self.stream.start()
    
    def processing_loop(self):
        # print("Processing loop entered...")

        """Main processing loop"""
        while self.running:
            # print("Buffer ready:", self.buffer_ready)

            if self.buffer_ready:
                self.process_audio()
                self.buffer_ready = False
            time.sleep(0.05)
    
    def run(self):
        # print("Processing thread starting...")

        """Start the tracker"""
        self.running = True
        self.start_stream()
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start live plot thread
#         self.plot_thread = threading.Thread(target=self.live_plot)
#         self.plot_thread.daemon = True
#         self.plot_thread.start()
        
        # Main loop to keep program running
        try:
            print("Hand tracking started! Move your hand toward or away from the microphone...")
            print("Press Ctrl+C to exit")
            
            # Keep main thread alive
            while self.running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.running = False
            self.plotting = False
            self.processing_thread.join(timeout=1.0)
            self.stream.stop()
            self.stream.close()
            self.save_plot("hand_movement_doppler.png")
            print("Tracker stopped")


if __name__ == "__main__":
    print("Hand Movement Tracker using Doppler Effect")
    print("------------------------------------------------")
    print("This program detects hand movements toward or away from the microphone")
    print("using the Doppler effect with acoustic signals.")
    
    # Install necessary packages if not already installed
    try:
        import sounddevice
        import numpy
        import scipy
    except ImportError:
        print("\nInstalling required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "sounddevice", "numpy", "scipy"])
        print("Packages installed successfully!")
    
    print("\nStarting tracker...")
    tracker = DopplerTracker()
    tracker.run()
    