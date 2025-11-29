sound and speed file.py
import socket
import struct
import errno
import time
import sounddevice as sd
import numpy as np
count=0
# --- Configuration ---
UDP_IP = "192.168.1.15" # Listen on all interfaces
UDP_PORT = 5001
MESSAGE_LENGTH = 13 # Bytes per UDP packet
sample_rate = 44100 # Audio sampling rate
duration = 0.5 # Duration of each audio snippet (in seconds)
min_amplitude = 1e-4 # Threshold to ignore silence
mass = 850 # Vehicle mass in kg
# --- Setup UDP socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(False)
sock.bind((UDP_IP, UDP_PORT))
# --- Data lists ---
speed_list = []
frequencies = []
# --- Frequency Detection Function ---
def detect_frequency(audio_data, rate):
 audio_data = audio_data.flatten()
 window = np.hanning(len(audio_data))
 audio_data = audio_data * window
 fft_spectrum = np.fft.rfft(audio_data)
 freq = np.fft.rfftfreq(len(audio_data), d=1/rate)
 amplitude = np.abs(fft_spectrum)
 if np.max(amplitude) < min_amplitude:
 return 0.0
 peak_idx = np.argmax(amplitude)
 return round(freq[peak_idx], 2)
# --- Record and return frequency ---
def get_audio_frequency():
 try:
 recording = sd.rec(int(sample_rate * duration), samplerate=sample_rate,
channels=1, dtype='float64')
 sd.wait()
 return detect_frequency(recording, sample_rate)
 except Exception as e:
 print("Microphone Error:", e)
 return 0.0
# --- Data Collection ---
i = 0
print(" Collecting speed and frequency data...")
while i < 30:
 newestData = None
 while True:
 try:
 data, _ = sock.recvfrom(MESSAGE_LENGTH)
 if data:
 newestData = data
 except socket.error as e:
 if e.errno == errno.EWOULDBLOCK:
 time.sleep(0.1)
 break
 else:
 raise e
 if newestData:
 speed_m_s = struct.unpack_from('<f', newestData, 1)[0]
 speed_kmh = round(speed_m_s * 3.6, 2)
 freq = get_audio_frequency()
 speed_list.append(speed_kmh)
 frequencies.append(freq)
 i += 1
 time.sleep(1)
# --- Final Output ---
print("\n Final Speed List (30 values):")
print("speed_list =", speed_list)
print("\n Final Frequency List (30 values):")
print("frequencies =", frequencies)
# --- Accident Detection Logic ---
def detect_instant_halt(lst):
 for i in range(1, len(lst)):
 if lst[i] == 0.0 and all(x == 0.0 for x in lst[i:]):
 return i
 return None
# Convert speed from km/h to m/s
speed_list_mps = [round(s / 3.6, 2) for s in speed_list]
halt_index = detect_instant_halt(speed_list_mps)
if halt_index is not None:
 time_taken = halt_index # seconds
 max_speed_mps = max(speed_list_mps)
 thrust = round((mass * max_speed_mps) / time_taken, 2) if time_taken > 0 else 0
 if thrust > 70500:
 if halt_index < len(frequencies):
 freq_at_halt = frequencies[halt_index]
 max_freq = max(frequencies)
 if freq_at_halt == max_freq and freq_at_halt > 1500:
 print("\n Accident Detected!")
 print(f" Speed before impact: {round(max_speed_mps * 3.6, 2)} km/h")
 print(f" Frequency generated: {freq_at_halt} Hz")
 print(f" Calculated Thrust: {thrust} N")
 count+=1
 else:
 print("\n Thrust high, but frequency doesn't confirm accident.")
 else:
 print("\n Frequency data unavailable at halt index.")
 else:
 print("\n Halt detected, but thrust too low to be considered an accident.")
else:
 print("\n No instant halt detected. Thrust and accident check skipped.")
# --- Additional Accident Check: Frequency Peak + Gradual Speed Drop ---
peak_freq = max(frequencies)
peak_freq_index = frequencies.index(peak_freq)
if peak_freq > 1500:
 # Check if from the peak index, speed drops continuously to 0 within 510 seconds
 max_check_range = 10
 remaining_samples = len(speed_list_mps) - peak_freq_index
 # Limit the check to available data, at most 10
 check_range = min(max_check_range, remaining_samples)
 speed_segment = speed_list_mps[peak_freq_index:peak_freq_index + check_range]
 if len(speed_segment) >= 5 and speed_segment[-1] == 0.0:
 # Check for monotonic decrease
 if all(earlier >= later for earlier, later in zip(speed_segment,
speed_segment[1:])):
 print("\n Accident Detected by Pattern!")
 print(f" Peak Frequency: {peak_freq} Hz at index {peak_freq_index}")
 print(f" Speed dropped to 0 in {len(speed_segment)} seconds")
 print(f" Speed before drop: {round(speed_segment[0] * 3.6, 2)} km/h")
 count+=1
 else:
 print("\n Frequency spike detected but speed did not drop consistently.")
 else:
 print("\n Frequency spike detected but speed did not reach 0 within 510
seconds.")
else:
 print("\n No significant frequency spike detected (<= 1500 Hz).")
print(count)
 
hospital.py
import geocoder
import requests
import re
# --- Step 1: Detect Location ---
g = geocoder.ip('me')
if g.ok and g.city:
 city = g.city
 lat, lng = g.latlng
 print(f"\n Detected Location: {city} (Lat: {lat}, Lon: {lng})\n")
else:
 city = "Lucknow"
 print(" Could not detect your location. Defaulting to 'Lucknow'")
# --- Step 2: SerpAPI Search ---
API_KEY = "184f49488fc15fc769bfe240026bb3276f8595943f657e121b6d455f4fcdca7c"
query = f"hospitals near {city} with phone number"
params = {
 "q": query,
 "engine": "google",
 "api_key": "184f49488fc15fc769bfe240026bb3276f8595943f657e121b6d455f4fcdca7c",
 "google_domain": "google.com",
 "location": city,
 "hl": "en",
 "gl": "in"
}
url = "https://serpapi.com/search"
response = requests.get(url, params=params)
# --- Step 3: Extract and Display ---
if response.status_code == 200:
 data = response.json()
 results = data.get("organic_results", [])
 
 if results:
 print(" Nearby Hospitals:\n")
 for i, result in enumerate(results, 1):
 title = result.get("title", "No Title")
 snippet = result.get("snippet", "")
 
 # Extract phone numbers (common Indian formats)
 phones = re.findall(r'\b\d{10}\b|\b\d{3,5}[-\s]?\d{6,7}\b', snippet)
 phone_text = ', '.join(phones) if phones else "Phone not found"
 # Attempt to extract location (basic approximation)
 location_match = re.search(r'(New
Delhi|Delhi|Lucknow|Noida|Gurgaon|Ghaziabad|[A-Za-z\s]+ \d{6})', snippet)
 location = location_match.group(0) if location_match else city
 print(f"{i}. Hospital: {title}")
 print(f" Phone: {phone_text}")
 print(f" Location: {location}")
 print("-" * 60)
 else:
 print(" No hospital results found.")
else:
 print(f" API Error: {response.status_code} - {response.text}")