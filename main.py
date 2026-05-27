from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import json
from datetime datetime

app = Flask(__name__)
CORS(app)

# ========== CONFIGURATION ==========
OFFENSIVE_LINK = "https://www.documentingreality.com/forum/f10/"
REPORT_MESSAGE = "This user is sharing extreme violent content. Please permanently ban this account."
LOG_FILE = "bans.log"

# Session path for persistent WhatsApp login
SESSION_DIR = "/home/runner/whatsapp_session"
os.makedirs(SESSION_DIR, exist_ok=True)
# ===================================

def log_ban(target, status, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {target} - {status} - {details}\n")
    print(f"[LOG] {target} - {status}")

def setup_driver():
    """Setup Firefox driver on Replit"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument(f"--user-data-dir={SESSION_DIR}")
    options.set_preference("general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Geckodriver path on Replit
    service = Service(executable_path="/nix/store/*/bin/geckodriver")
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def is_session_valid(driver):
    """Check if WhatsApp session exists"""
    driver.get("https://web.whatsapp.com")
    time.sleep(5)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="chat-list"]'))
        )
        return True
    except:
        return False

def send_message(driver, target, message):
    """Send message to target"""
    try:
        search = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search.click()
        search.clear()
        search.send_keys(target)
        time.sleep(2)
        search.send_keys(Keys.ENTER)
        time.sleep(3)
        
        msg_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        msg_box.click()
        msg_box.send_keys(message)
        time.sleep(1)
        msg_box.send_keys(Keys.ENTER)
        time.sleep(2)
        return True
    except Exception as e:
        log_ban(target, "SEND_ERROR", str(e))
        return False

def report_last_message(driver, target):
    """Report the last sent message"""
    try:
        messages = driver.find_elements(By.XPATH, '//div[contains(@class, "message-out")]')
        if not messages:
            return False
        
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        actions.context_click(messages[-1]).perform()
        time.sleep(1)
        
        report_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="Report"]'))
        )
        report_btn.click()
        time.sleep(2)
        
        illegal = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Illegal content")]'))
        )
        illegal.click()
        time.sleep(2)
        
        textarea = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//textarea'))
        )
        textarea.send_keys(REPORT_MESSAGE)
        time.sleep(1)
        
        submit = driver.find_element(By.XPATH, '//button[@aria-label="Send"]')
        submit.click()
        return True
    except Exception as e:
        log_ban(target, "REPORT_ERROR", str(e))
        return False

def ban_target(target):
    """Full ban sequence"""
    driver = None
    try:
        driver = setup_driver()
        
        if not is_session_valid(driver):
            return {"success": False, "error": "WhatsApp session invalid. Admin needs to scan QR code once."}
        
        if not send_message(driver, target, OFFENSIVE_LINK):
            return {"success": False, "error": "Failed to send message"}
        
        time.sleep(3)
        
        if not report_last_message(driver, target):
            return {"success": False, "error": "Failed to submit report"}
        
        log_ban(target, "BANNED")
        return {"success": True, "message": f"Ban report submitted for {target}"}
    
    except Exception as e:
        log_ban(target, "ERROR", str(e))
        return {"success": False, "error": str(e)}
    finally:
        if driver:
            driver.quit()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "active", "service": "WhatsApp Ban API"})

@app.route('/api/ban', methods=['POST'])
def api_ban():
    data = request.get_json()
    target = data.get('number', '').strip()
    
    if not target:
        return jsonify({"success": False, "error": "No number provided"})
    
    if not target.startswith('+'):
        return jsonify({"success": False, "error": "Number must include country code (e.g., +1234567890)"})
    
    result = ban_target(target)
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def api_status():
    driver = None
    try:
        driver = setup_driver()
        valid = is_session_valid(driver)
        return jsonify({"session_valid": valid})
    except Exception as e:
        return jsonify({"session_valid": False, "error": str(e)})
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
