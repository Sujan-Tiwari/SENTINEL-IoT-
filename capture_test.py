import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "presentation_output", "screenshots"))

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

print(f"Connecting to Chrome webdriver...")
driver = webdriver.Chrome(options=options)
driver.set_window_size(1920, 1080)

try:
    print("Navigating to http://127.0.0.1:8501...")
    driver.get("http://127.0.0.1:8501")
    
    # Wait until Streamlit app finishes loading (wait for stSidebar or markdown element)
    print("Waiting for Streamlit app elements...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'SENTINEL-IoT') or contains(text(), 'Airspace')]"))
    )
    time.sleep(3)  # Allow charts and CSS animations to settle
    
    out_path = os.path.join(SCREENSHOTS_DIR, "00_test_homepage.png")
    driver.save_screenshot(out_path)
    print(f"Screenshot successfully saved: {out_path} (size: {os.path.getsize(out_path)} bytes)")
finally:
    driver.quit()
