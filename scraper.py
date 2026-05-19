import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from utils import extract_otp_from_text, clean_phone_number, clean_service_name

class IVASMSScraper:
    """Scraper for IVASMS.com to fetch OTPs and messages"""
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://www.ivasms.com"
        self.is_logged_in = False
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def login(self):
        """Login to IVASMS account"""
        try:
            print(f"Attempting to login to IVASMS with email: {self.email}")
            
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                print(f"Failed to access login page. Status: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            csrf_token = None
            csrf_input = soup.find('input', {'name': '_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            login_data = {
                'email': self.email,
                'password': self.password,
            }
            
            if csrf_token:
                login_data['_token'] = csrf_token
            
            login_response = self.session.post(login_url, data=login_data)
            
            if login_response.status_code == 200:
                if 'dashboard' in login_response.url.lower() or 'account' in login_response.url.lower():
                    self.is_logged_in = True
                    print("Successfully logged in to IVASMS")
                    return True
                
                soup = BeautifulSoup(login_response.content, 'html.parser')
                if soup.find(text=re.compile(r'dashboard|account|logout', re.I)):
                    self.is_logged_in = True
                    print("Successfully logged in to IVASMS")
                    return True
            
            print("Login failed - invalid credentials or site structure changed")
            return False
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def fetch_messages(self):
        """Fetch recent messages/OTPs from account"""
        if not self.is_logged_in:
            if not self.login():
                return []
        
        try:
            possible_paths = [
                '/messages',
                '/sms',
                '/history',
                '/dashboard',
                '/account',
                '/numbers'
            ]
            
            messages = []
            
            for path in possible_paths:
                try:
                    url = f"{self.base_url}{path}"
                    response = self.session.get(url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        page_messages = self._extract_messages_from_page(soup)
                        if page_messages:
                            messages.extend(page_messages)
                            print(f"Found {len(page_messages)} messages on {path}")
                            break
                except Exception:
                    continue
            
            if not messages:
                dashboard_response = self.session.get(f"{self.base_url}/dashboard")
                if dashboard_response.status_code == 200:
                    soup = BeautifulSoup(dashboard_response.content, 'html.parser')
                    messages = self._extract_messages_from_page(soup)
            
            return messages
            
        except Exception as e:
            print(f"Error fetching messages: {e}")
            self.is_logged_in = False  # Force re-login on next call
            return []
    
    def _extract_messages_from_page(self, soup):
        """Extract message data from a BeautifulSoup page object"""
        messages = []
        
        try:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        message_data = self._extract_message_from_row(cells)
                        if message_data:
                            messages.append(message_data)
            
            message_divs = soup.find_all('div', class_=re.compile(r'message|sms|otp', re.I))
            for div in message_divs:
                message_data = self._extract_message_from_div(div)
                if message_data:
                    messages.append(message_data)
            
            text_content = soup.get_text()
            potential_otps = re.findall(r'\b\d{4,6}\b', text_content)
            if potential_otps:
                for otp in potential_otps[:5]:
                    message_data = {
                        'otp': otp,
                        'phone': self._extract_phone_from_context(text_content, otp),
                        'service': self._extract_service_from_context(text_content, otp),
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'raw_message': f"OTP: {otp}"
                    }
                    messages.append(message_data)
            
        except Exception as e:
            print(f"Error extracting messages from page: {e}")
        
        return messages
    
    def _extract_message_from_row(self, cells):
        """Extract message data from table row cells"""
        try:
            if len(cells) < 3:
                return None
            
            phone = ""
            service = ""
            message = ""
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                
                if re.search(r'\+?\d{10,15}', cell_text):
                    phone = clean_phone_number(cell_text)
                elif re.search(r'facebook|google|instagram|twitter|whatsapp|telegram|discord', cell_text, re.I):
                    service = clean_service_name(cell_text)
                elif len(cell_text) > 20:
                    message = cell_text
                elif re.search(r'\d{1,2}:\d{2}', cell_text):
                    timestamp = cell_text
            
            otp = extract_otp_from_text(message)
            
            if otp:
                return {
                    'otp': otp,
                    'phone': phone or "N/A",
                    'service': service or "Unknown",
                    'timestamp': timestamp,
                    'raw_message': message
                }
        
        except Exception as e:
            print(f"Error extracting from row: {e}")
        
        return None
    
    def _extract_message_from_div(self, div):
        """Extract message data from div container"""
        try:
            text = div.get_text(strip=True)
            
            otp = extract_otp_from_text(text)
            if not otp:
                return None
            
            phone_match = re.search(r'\+?\d{10,15}', text)
            phone = clean_phone_number(phone_match.group()) if phone_match else "N/A"
            
            service_match = re.search(r'(facebook|google|instagram|twitter|whatsapp|telegram|discord)', text, re.I)
            service = clean_service_name(service_match.group()) if service_match else "Unknown"
            
            return {
                'otp': otp,
                'phone': phone,
                'service': service,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'raw_message': text
            }
        
        except Exception as e:
            print(f"Error extracting from div: {e}")
        
        return None
    
    def _extract_phone_from_context(self, text, otp):
        """Extract phone number from context around OTP"""
        otp_index = text.find(otp)
        if otp_index != -1:
            context = text[max(0, otp_index-100):otp_index+100]
            phone_match = re.search(r'\+?\d{10,15}', context)
            if phone_match:
                return clean_phone_number(phone_match.group())
        return "N/A"
    
    def _extract_service_from_context(self, text, otp):
        """Extract service name from context around OTP"""
        otp_index = text.find(otp)
        if otp_index != -1:
            context = text[max(0, otp_index-100):otp_index+100].lower()
            services = ['facebook', 'google', 'instagram', 'twitter', 'whatsapp', 'telegram', 'discord']
            for service in services:
                if service in context:
                    return clean_service_name(service)
        return "Unknown"
    
    def test_connection(self):
        """Test connection to IVASMS"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False


def create_scraper(email, password):
    """
    Factory function to create and verify scraper.

    FIX: Previously only tested connectivity, not login. Now also verifies
    that the login succeeds before returning the scraper instance. Returns
    None if either step fails, so the caller knows initialization failed.
    """
    scraper = IVASMSScraper(email, password)
    
    if not scraper.test_connection():
        print("Warning: Cannot connect to IVASMS.com — check network or site availability")
        return None
    
    if not scraper.login():
        print("Warning: IVASMS login failed — check IVASMS_EMAIL and IVASMS_PASSWORD env vars")
        return None
    
    return scraper


def test_scraper():
    """Test the scraper with dummy data"""
    email = "samicdeym@gmail.com"
    password = "c59FiuhM54%6%Mf"
    
    scraper = create_scraper(email, password)
    if scraper:
        messages = scraper.fetch_messages()
        print(f"Found {len(messages)} messages")
        for msg in messages:
            print(f"OTP: {msg['otp']}, Phone: {msg['phone']}, Service: {msg['service']}")
    else:
        print("Failed to create scraper")

if __name__ == "__main__":
    test_scraper()
