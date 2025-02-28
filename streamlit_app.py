import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.signal as signal
from pyteomics import mzml
import re
import streamlit as st


url = "https://zenodo.org/records/10211590/files/D141_POS.mzML"
start_byte = 56_068_462 - 1_000_000
end_byte = 56_068_462 - 1
headers = {"Range": f"bytes={start_byte}-{end_byte}"}
response = requests.get(url, headers=headers, stream=True)
response.raise_for_status()

with open("indexed_part.mzML", "wb") as f:
   for chunk in response.iter_content(chunk_size=8192):
       f.write(chunk)

with open("indexed_part.mzML", "r", encoding="utf-8") as f:
   text = f.read()

# If text contains <offset idRef="abc123">456</offset> then matches stores ('abc123', '456')
matches = re.findall(r'<offset idRef="([^"]+)">(\d+)</offset>', text)
scan_offsets = {scan_id: int(offset) for scan_id, offset in matches}
scan_list = list(scan_offsets.items())
print("Scan offsets found:", scan_list[:5])
last_key = None
for key in reversed(scan_offsets):
   if 'scan=' in key:
      last_key = key
      break
if last_key is None:
   raise ValueError("No key containing 'scan=' found in scan_offsets")
max_scan = int(last_key.split('scan=')[1].split(' ')[0])

# Run the Streamlit app
if __name__ == "__main__":
   st.title("mzML Scan Viewer")
   desired_scan = st.text_input(f"Enter a scan number between 1 and {max_scan} or type q to quit:")
   if desired_scan == "":
      st.write(f"Please enter a scan number between 1 and {max_scan} or type q to quit.")
   elif desired_scan == "q":
      st.write("Quitting the application.")
      st.stop()
   else:
      if not desired_scan.isdigit() or int(desired_scan) < 0 or int(desired_scan) > max_scan:
         st.error("Invalid scan number. Please enter an integer within the given range.")
      else:
         if desired_scan.startswith('0'):
            desired_scan = desired_scan.lstrip('0')
         st.write(f"Desired scan: {desired_scan}")
         end_scan = str(int(desired_scan) + 1)
         target_scan_id = "controllerType=0 controllerNumber=1 scan=" + desired_scan
         end_scan_id = "controllerType=0 controllerNumber=1 scan=" + end_scan
         scan_start = scan_offsets[target_scan_id]
         scan_end = scan_offsets[end_scan_id] - 10 if end_scan_id in scan_offsets else 10000

         # Request the specific scan range from the server
         headers = {"Range": f"bytes={scan_start}-{scan_end}"}
         response = requests.get(url, headers=headers, stream=True)
         response.raise_for_status()

         with open("target_scan.mzML", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
               f.write(chunk)
         print(f"Downloaded scan {target_scan_id}")

         with mzml.read("target_scan.mzML") as reader:
            for spectrum in reader:
               if spectrum['id'] == target_scan_id:
                  mz_values = spectrum['m/z array']
                  intensity_values = spectrum['intensity array']
                  st.write(f"m/z values: {mz_values}")
                  st.write(f"Intensity values: {intensity_values}")

                  plt.figure(figsize=(10, 6))
                  plt.plot(mz_values, intensity_values)
                  plt.xlabel('m/z')
                  plt.ylabel('Intensity')
                  plt.title(f'Scan {desired_scan}')
         st.pyplot(plt)