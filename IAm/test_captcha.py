#!/usr/bin/env python3
"""
Advanced Test Script for IAm Captcha Passive Mode Detection.
Evolves evasion techniques to stress-test the detection system.

EVOLUTION 2: Targeting stack_has_eval and mouse movement detection
"""

import time
import random
import math
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://127.0.0.1:8080"


def human_like_mouse_movement(driver, element, duration=0.5):
    """Original human-like mouse movement (kept for comparison)"""
    actions = ActionChains(driver)
    
    start_x, start_y = 100, 100
    location = element.location
    size = element.size
    end_x = location['x'] + size['width'] // 2
    end_y = location['y'] + size['height'] // 2
    
    ctrl1_x = start_x + (end_x - start_x) * 0.3 + random.randint(-50, 50)
    ctrl1_y = start_y + (end_y - start_y) * 0.1 + random.randint(-30, 30)
    ctrl2_x = start_x + (end_x - start_x) * 0.7 + random.randint(-50, 50)
    ctrl2_y = start_y + (end_y - start_y) * 0.9 + random.randint(-30, 30)
    
    steps = int(duration * 60)
    
    for i in range(steps):
        t = i / steps
        x = (1-t)**3 * start_x + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * end_x
        y = (1-t)**3 * start_y + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * end_y
        
        jitter_x = random.gauss(0, 0.5)
        jitter_y = random.gauss(0, 0.5)
        speed_factor = 1.0 - 0.5 * (t ** 2)
        
        actions.move_by_offset(int(x - start_x + jitter_x), int(y - start_y + jitter_y))
        start_x, start_y = x, y
        time.sleep((1/60) * speed_factor + random.uniform(0, 0.01))
    
    actions.perform()


def human_like_mouse_movement_v2(driver, element, duration=1.5):
    """
    Evolved human-like mouse movement with:
    - Variable timing intervals (not uniform)
    - More natural velocity curves
    - Micro-pauses and hesitations
    """
    # Get viewport size for realistic starting position
    viewport_width = driver.execute_script("return window.innerWidth")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    # Start from a random but realistic position
    start_x = random.randint(int(viewport_width * 0.3), int(viewport_width * 0.7))
    start_y = random.randint(int(viewport_height * 0.2), int(viewport_height * 0.5))
    
    # Move to starting position first
    actions = ActionChains(driver)
    actions.move_by_offset(start_x, start_y).perform()
    time.sleep(random.uniform(0.1, 0.3))
    
    # Get target position
    location = element.location
    size = element.size
    end_x = location['x'] + size['width'] // 2
    end_y = location['y'] + size['height'] // 2
    
    # Calculate relative movement needed
    dx = end_x - start_x
    dy = end_y - start_y
    
    # Generate control points for bezier with more randomness
    ctrl1_x = dx * random.uniform(0.2, 0.4) + random.randint(-30, 30)
    ctrl1_y = dy * random.uniform(0.0, 0.2) + random.randint(-20, 20)
    ctrl2_x = dx * random.uniform(0.6, 0.8) + random.randint(-30, 30)
    ctrl2_y = dy * random.uniform(0.8, 1.0) + random.randint(-20, 20)
    
    # Variable number of steps (not fixed)
    base_steps = int(duration * random.uniform(40, 80))
    
    current_x, current_y = 0, 0
    actions = ActionChains(driver)
    
    i = 0
    while i < base_steps:
        t = i / base_steps
        
        # Cubic bezier formula
        target_x = (1-t)**3 * 0 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * dx
        target_y = (1-t)**3 * 0 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * dy
        
        # Add natural jitter that varies with speed
        speed = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        jitter_scale = max(0.3, min(2.0, speed * 0.1))
        jitter_x = random.gauss(0, jitter_scale)
        jitter_y = random.gauss(0, jitter_scale)
        
        move_x = int(target_x - current_x + jitter_x)
        move_y = int(target_y - current_y + jitter_y)
        
        if move_x != 0 or move_y != 0:
            actions.move_by_offset(move_x, move_y)
            current_x += move_x
            current_y += move_y
        
        # Variable timing - key to avoiding uniform interval detection
        if random.random() < 0.1:
            # Occasional micro-pause (hesitation)
            pause = random.uniform(0.05, 0.2)
        elif t > 0.8:
            # Slow down near target
            pause = random.uniform(0.02, 0.08)
        else:
            # Normal movement with high variance
            pause = random.uniform(0.005, 0.04)
        
        actions.pause(pause)
        
        # Sometimes skip steps (acceleration)
        if random.random() < 0.15:
            i += random.randint(1, 3)
        else:
            i += 1
    
    actions.perform()


def get_advanced_stealth_options():
    """Original stealth options (kept for comparison)"""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return options


def get_advanced_stealth_options_v2():
    """Get Chrome options with advanced stealth configurations - updated UA"""
    options = Options()
    
    # Disable automation flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Make it look more like a real browser
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Use current Chrome version in UA
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")
    
    return options


ADVANCED_STEALTH_JS = """
// Advanced stealth script - attempts to evade detection
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

Object.defineProperty(Navigator.prototype, 'webdriver', {
    get: () => undefined,
    configurable: false,
    enumerable: true
});

if (!window.chrome) {
    window.chrome = {};
}
window.chrome.runtime = { connect: function() {}, sendMessage: function() {} };
window.chrome.csi = function() { return {}; };
window.chrome.loadTimes = function() { return {}; };

Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' }
        ];
        plugins.length = 3;
        return plugins;
    }
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

const originalToString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === Function.prototype.toString) {
        return 'function toString() { [native code] }';
    }
    if (this === navigator.permissions.query) {
        return 'function query() { [native code] }';
    }
    return originalToString.call(this);
};

const originalError = Error;
window.Error = function(...args) {
    const error = new originalError(...args);
    if (error.stack) {
        error.stack = error.stack.replace(/selenium|webdriver|puppeteer|playwright|cypress/gi, 'browser');
    }
    return error;
};
"""


ULTRA_STEALTH_JS = """
// Ultra stealth - deeper evasion techniques
const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
Object.getOwnPropertyDescriptor = function(obj, prop) {
    if (obj === navigator && prop === 'webdriver') {
        return undefined;
    }
    return originalGetOwnPropertyDescriptor.call(this, obj, prop);
};

Object.defineProperty(Object, 'getOwnPropertyDescriptor', {
    value: Object.getOwnPropertyDescriptor,
    writable: false,
    configurable: false
});

const originalHasOwnProperty = Object.prototype.hasOwnProperty;
Object.prototype.hasOwnProperty = function(prop) {
    if (this === navigator && prop === 'webdriver') {
        return false;
    }
    return originalHasOwnProperty.call(this, prop);
};

if (typeof Reflect !== 'undefined') {
    const originalReflectGet = Reflect.get;
    Reflect.get = function(target, prop, receiver) {
        if (target === navigator && prop === 'webdriver') {
            return undefined;
        }
        return originalReflectGet.call(this, target, prop, receiver);
    };
}
"""


# Evolution 2: Try to hide eval from stack traces
STACK_EVASION_JS = """
// Attempt to hide eval/anonymous from error stacks
// This targets the stack_has_eval detection

(function() {
    // Store original Error
    const OriginalError = Error;
    
    // Create a wrapper that cleans stack traces
    function CleanError(message) {
        const error = new OriginalError(message);
        
        // Clean the stack trace
        if (error.stack) {
            error.stack = error.stack
                .split('\\n')
                .filter(line => {
                    const lower = line.toLowerCase();
                    return !lower.includes('eval') && 
                           !lower.includes('<anonymous>') &&
                           !lower.includes('__puppeteer') &&
                           !lower.includes('__selenium');
                })
                .join('\\n');
        }
        
        return error;
    }
    
    // Copy prototype
    CleanError.prototype = OriginalError.prototype;
    CleanError.captureStackTrace = OriginalError.captureStackTrace;
    CleanError.stackTraceLimit = OriginalError.stackTraceLimit;
    
    // Replace global Error
    window.Error = CleanError;
    
    // Also intercept Error.prepareStackTrace if it exists (V8)
    if (OriginalError.prepareStackTrace) {
        const originalPrepare = OriginalError.prepareStackTrace;
        Error.prepareStackTrace = function(error, structuredStackTrace) {
            // Filter out eval frames
            const filtered = structuredStackTrace.filter(frame => {
                const fn = frame.getFunctionName() || '';
                const file = frame.getFileName() || '';
                return !fn.includes('eval') && 
                       !file.includes('eval') &&
                       !file.includes('<anonymous>');
            });
            return originalPrepare(error, filtered);
        };
    }
})();

// Override navigator.webdriver on prototype level
delete Navigator.prototype.webdriver;
Object.defineProperty(Navigator.prototype, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// Ensure chrome object looks real
window.chrome = window.chrome || {};
window.chrome.app = window.chrome.app || { isInstalled: false, getDetails: () => null, installState: () => 'not_installed' };
window.chrome.csi = window.chrome.csi || function() { return {}; };
window.chrome.loadTimes = window.chrome.loadTimes || function() { return {}; };
window.chrome.runtime = window.chrome.runtime || { connect: () => {}, sendMessage: () => {} };
"""


# Evolution 2: More sophisticated stealth that doesn't use eval patterns
STEALTH_NO_EVAL_JS = """
// Stealth script designed to not trigger eval detection
// Uses IIFE pattern that compiles to native-looking code

;(function(nav, win, doc) {
    'use strict';
    
    // Webdriver removal using delete + defineProperty
    try {
        delete nav.webdriver;
    } catch(e) {}
    
    var desc = {
        get: function() { return undefined; },
        configurable: true,
        enumerable: true
    };
    
    try {
        Object.defineProperty(nav, 'webdriver', desc);
    } catch(e) {}
    
    try {
        Object.defineProperty(Navigator.prototype, 'webdriver', desc);
    } catch(e) {}
    
    // Languages fix
    if (!nav.languages || nav.languages.length === 0) {
        Object.defineProperty(nav, 'languages', {
            get: function() { return ['en-US', 'en']; }
        });
    }
    
    // Plugins fix - create realistic plugin array
    var fakePlugins = {
        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        2: { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        length: 3,
        item: function(i) { return this[i] || null; },
        namedItem: function(n) { 
            for (var i = 0; i < this.length; i++) {
                if (this[i] && this[i].name === n) return this[i];
            }
            return null;
        },
        refresh: function() {}
    };
    
    try {
        Object.defineProperty(nav, 'plugins', {
            get: function() { return fakePlugins; }
        });
    } catch(e) {}
    
})(navigator, window, document);
"""


def test_level_1_basic():
    """Level 1: Basic Selenium - should be easily detected"""
    print("\n" + "="*60)
    print("LEVEL 1: Basic Selenium (Easy Detection)")
    print("="*60)
    
    driver = webdriver.Chrome()
    try:
        run_captcha_test(driver, "Level 1")
    finally:
        driver.quit()


def test_level_2_stealth_options():
    """Level 2: Stealth Chrome options with evolved mouse movement"""
    print("\n" + "="*60)
    print("LEVEL 2: Stealth Chrome Options (Evolved)")
    print("="*60)
    
    options = get_advanced_stealth_options_v2()
    driver = webdriver.Chrome(options=options)
    
    try:
        run_captcha_test(driver, "Level 2", use_human_mouse=True, mouse_version=2)
    finally:
        driver.quit()


def test_level_3_cdp_stealth():
    """Level 3: CDP commands to hide webdriver"""
    print("\n" + "="*60)
    print("LEVEL 3: CDP Stealth (webdriver=undefined)")
    print("="*60)
    
    options = get_advanced_stealth_options()
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    try:
        run_captcha_test(driver, "Level 3")
    finally:
        driver.quit()


def test_level_4_advanced_stealth():
    """Level 4: Advanced stealth with multiple evasions"""
    print("\n" + "="*60)
    print("LEVEL 4: Advanced Stealth (Multiple Evasions)")
    print("="*60)
    
    options = get_advanced_stealth_options()
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": ADVANCED_STEALTH_JS
    })
    
    try:
        run_captcha_test(driver, "Level 4", use_human_mouse=True)
    finally:
        driver.quit()


def test_level_5_ultra_stealth():
    """Level 5: Ultra stealth with deep evasions"""
    print("\n" + "="*60)
    print("LEVEL 5: Ultra Stealth (Deep Evasions)")
    print("="*60)
    
    options = get_advanced_stealth_options()
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": ADVANCED_STEALTH_JS + "\n" + ULTRA_STEALTH_JS
    })
    
    try:
        run_captcha_test(driver, "Level 5", use_human_mouse=True, extra_delay=True)
    finally:
        driver.quit()


def test_level_6_undetected_chromedriver():
    """Level 6: Using undetected-chromedriver with evolved techniques"""
    print("\n" + "="*60)
    print("LEVEL 6: Undetected ChromeDriver (Evolved)")
    print("="*60)
    
    import undetected_chromedriver as uc
    
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options)
    
    try:
        run_captcha_test(driver, "Level 6", use_human_mouse=True, mouse_version=2, extra_delay=True)
    finally:
        driver.quit()


def test_level_7_stack_evasion():
    """Level 7: Specifically targeting stack_has_eval detection"""
    print("\n" + "="*60)
    print("LEVEL 7: Stack Trace Evasion")
    print("="*60)
    
    options = get_advanced_stealth_options_v2()
    driver = webdriver.Chrome(options=options)
    
    # Inject stack evasion script
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": STACK_EVASION_JS
    })
    
    try:
        run_captcha_test(driver, "Level 7", use_human_mouse=True, mouse_version=2, extra_delay=True)
    finally:
        driver.quit()


def test_level_8_no_cdp():
    """Level 8: Avoid CDP injection entirely - use runtime script injection"""
    print("\n" + "="*60)
    print("LEVEL 8: No CDP Injection (Runtime Only)")
    print("="*60)
    
    options = get_advanced_stealth_options_v2()
    driver = webdriver.Chrome(options=options)
    
    try:
        # Load page first WITHOUT any CDP scripts
        driver.get(f"{BASE_URL}/login")
        print(f"✓ Loaded page")
        
        # Inject stealth AFTER page load via execute_script (not CDP)
        # This might avoid the eval detection since it runs in page context
        driver.execute_script(STEALTH_NO_EVAL_JS)
        
        time.sleep(3)  # Let passive tracking collect data
        
        # Continue with test
        run_captcha_test_no_load(driver, "Level 8", use_human_mouse=True, mouse_version=2)
    finally:
        driver.quit()


def run_captcha_test(driver, level_name, use_human_mouse=False, mouse_version=1, extra_delay=False):
    """Run the captcha test with the given driver"""
    try:
        driver.get(f"{BASE_URL}/login")
        print(f"✓ Loaded page")
        
        if extra_delay:
            time.sleep(3)
        else:
            time.sleep(2)
        
        run_captcha_test_no_load(driver, level_name, use_human_mouse, 1)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def run_captcha_test_no_load(driver, level_name, use_human_mouse=False, mouse_version=1):
    """Run the captcha test without loading the page (already loaded)"""
    try:
        # Click Create Account
        create_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Create Account')]"))
        )
        create_link.click()
        print("✓ Clicked 'Create Account'")
        
        time.sleep(1)
        
        # Find captcha
        captcha = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "iam-captcha"))
        )
        
        if use_human_mouse:
            print(f"  Simulating human mouse movement (v{mouse_version})...")
            try:
                if mouse_version == 2:
                    human_like_mouse_movement_v2(driver, captcha, duration=1.5)
                else:
                    human_like_mouse_movement(driver, captcha, duration=0.8)
            except Exception as e:
                print(f"  (Mouse simulation failed: {e})")
                # Fallback with variable timing
                actions = ActionChains(driver)
                for _ in range(random.randint(15, 25)):
                    actions.move_by_offset(
                        random.randint(-15, 15),
                        random.randint(-15, 15)
                    ).pause(random.uniform(0.01, 0.1))
                actions.perform()
        else:
            # Basic mouse movement
            actions = ActionChains(driver)
            actions.move_to_element(captcha).perform()
            time.sleep(0.3)
        
        # Click checkbox
        checkbox = driver.find_element(By.CLASS_NAME, "iam-checkbox-container")
        checkbox.click()
        print("✓ Clicked captcha checkbox")
        
        time.sleep(3)
        
        # Check result
        check_result(driver, level_name)
        
        # Save screenshot
        filename = f"test_result_{level_name.lower().replace(' ', '_')}.png"
        driver.save_screenshot(filename)
        print(f"✓ Screenshot: {filename}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def check_result(driver, level_name):
    """Check if the captcha was bypassed or detected"""
    try:
        challenge = driver.find_element(By.CLASS_NAME, "iam-challenge")
        is_open = "open" in challenge.get_attribute("class")
        
        if is_open:
            print(f"✓ DETECTED - Visual challenge opened")
            print(f"  {level_name} evasion was caught!")
            return False
        else:
            checkbox = driver.find_element(By.CLASS_NAME, "iam-checkbox")
            if "checked" in checkbox.get_attribute("class"):
                print(f"✗ BYPASSED - Captcha passed without challenge!")
                print(f"  {level_name} evasion succeeded - DETECTION NEEDS IMPROVEMENT")
                return True
            else:
                print(f"? UNKNOWN - Neither challenged nor verified")
                return None
    except NoSuchElementException:
        print("? Could not determine result")
        return None

def main():
    """Run all tests"""
    print("="*60)
    print("IAm Captcha - Advanced Evasion Test Suite (Evolution 2)")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print("Make sure the server is running!")
    print("\nThis test suite progressively increases evasion sophistication")
    print("to stress-test the passive detection system.\n")
    print("New in Evolution 2:")
    print("  - Variable mouse timing to avoid uniform interval detection")
    print("  - Stack trace evasion to hide eval/anonymous")
    print("  - Runtime injection to avoid CDP detection")
    print()
    
    # Browser tests - progressive difficulty
    tests = [
        ("Level 1", test_level_1_basic),
        ("Level 2", test_level_2_stealth_options),
        ("Level 3", test_level_3_cdp_stealth),
        ("Level 4", test_level_4_advanced_stealth),
        ("Level 5", test_level_5_ultra_stealth),
        ("Level 6", test_level_6_undetected_chromedriver),
        ("Level 7", test_level_7_stack_evasion),
        ("Level 8", test_level_8_no_cdp),
    ]
    
    for name, test_func in tests:
        try:
            test_func()
            input(f"\nPress Enter to continue to next test...")
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
            break
        except Exception as e:
            print(f"\n✗ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test Suite Complete!")
    print("="*60)
    print("\nReview the screenshots and results above.")
    print("Any 'BYPASSED' results indicate detection gaps that need fixing.")


if __name__ == "__main__":
    main()
