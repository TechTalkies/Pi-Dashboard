import sys
import time
import requests
import json
import pygame
import os
import io
from flask import Flask, request, jsonify, render_template
from threading import Thread
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# config
LARGE_FONT = 62
MEDIUM_FONT = 40
SMALL_FONT = 30

quote_text = "Tech Talkies Dashboard"

# Initialize API_URL, LAT, LON, and tasks as global variables.  These will be loaded from config.json
API_URL = ""
LAT = 0
LON = 0
tasks = []
data_file_path = 'config.json'  # Path to your data file.  Make sure this is correct!
last_modified_time = 0
API_KEY = ""
update_weather = True
update_ToDo = True

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((480, 320), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
clock = pygame.time.Clock()

# Font sizes
font_large = pygame.font.Font('Poppins-Regular.ttf', LARGE_FONT)
font_medium = pygame.font.Font('Poppins-Regular.ttf', MEDIUM_FONT)
font_small = pygame.font.Font('Poppins-Regular.ttf', SMALL_FONT)
font_toDo = pygame.font.Font('seguisym.ttf', SMALL_FONT)

# Tile and padding configuration
padding = 10
tile_width = (screen_width - 3 * padding) // 2
quote_bar_height = 60

available_height = screen_height - 3 * padding - quote_bar_height
tile_height = (available_height - padding) // 2

# define tile positions
time_tile_rect = (padding, padding, tile_width, tile_height)
weather_tile_rect = (padding, padding * 2 + tile_height, tile_width, tile_height)
todo_tile_rect = (2 * padding + tile_width, padding, tile_width, 2 * tile_height + padding)
quote_bar_rect = (padding, screen_height - padding - quote_bar_height, screen_width - 2 * padding, quote_bar_height)

# Keep track of the last update times
last_time_update = time.time()
last_second_update = time.time()
last_weather_update = 0
update_interval = 300  # seconds (5 minutes)

# Store the time and date, updating them only once per minute
current_time = time.strftime("%I:%M %p")
day_date = time.strftime("%A, %d")
seconds = time.strftime("%S")

# Global variable to store weather data
weather_data = None
data_loaded = False  # flag to check if initial data load is complete

config_data = {
    'apiKey': "",  # String, so double quotes are correct
    'latitude': 0, # Integer, no quotes
    'longitude': 0, # Integer, no quotes
    'tasks': []    # List, no quotes (but elements *inside* could be strings)
}

# Flask app initialization
app = Flask(__name__, template_folder='.')  # Important:  Set template folder if needed

def resetConfig():
    global config_data
    config_data = {
        'apiKey': "",  # String, so double quotes are correct
        'latitude': 0, # Integer, no quotes
        'longitude': 0, # Integer, no quotes
        'tasks': []    # List, no quotes (but elements *inside* could be strings)
    }

# Function to fetch weather data from OpenWeatherMap API
def fetch_weather():
    """Fetches weather data from OpenWeatherMap API."""
    global API_URL
    try:
        if not API_URL:
            return None
        r = requests.get(API_URL)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching weather: {e}")
        return None
    except Exception as e:
        logging.error(f"Error fetching weather: {e}")
        return None

def draw_tile(rect, color, lines, font, radius=12, align="center"):
    """Draws a tile with rounded corners and text."""
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    rendered_lines = [font.render(str(text), True, (255, 255, 255)) for text in lines]
    total_height = sum(line.get_height() for line in rendered_lines)
    start_y = rect[1] + (rect[3] - total_height) // 2

    for line in rendered_lines:
        if align == "center":
            label_rect = line.get_rect(center=(rect[0] + rect[2] // 2, start_y + line.get_height() // 2))
        elif align == "left":
            label_rect = line.get_rect(midleft=(rect[0] + 10, start_y + line.get_height() // 2))  # 10px padding
        elif align == "right":
            label_rect = line.get_rect(midright=(rect[0] + rect[2] - 10, start_y + line.get_height() // 2))  # 10px padding
        else:
            raise ValueError("Invalid alignment. Use 'center', 'left', or 'right'.")

        screen.blit(line, label_rect)
        start_y += line.get_height()


# Function to draw the quote bar at the bottom of the screen
def draw_quote_bar():
    """Draws the quote bar at the bottom of the screen."""
    global quote_text
    pygame.draw.rect(screen, (231, 175, 59), quote_bar_rect, border_radius=12)
    quote_surface = font_medium.render(quote_text, True, (255, 255, 255))
    quote_rect = quote_surface.get_rect(center=(quote_bar_rect[0] + quote_bar_rect[2] // 2, quote_bar_rect[1] + quote_bar_rect[3] // 2))
    screen.blit(quote_surface, quote_rect)

# Function to draw the time tile
def draw_time_tile():
    """Draws the time tile."""
    global current_time, day_date, seconds

    current_time_new = time.strftime("%I:%M %p")
    day_date_new = time.strftime("%A, %d")
    seconds_new = time.strftime("%S")

    if current_time != current_time_new or day_date != day_date_new:
        current_time = current_time_new
        day_date = day_date_new

    time_lines = [current_time,""]
    draw_tile(time_tile_rect, (235, 123, 52) , time_lines, font_large)

    time_height = font_large.get_height()
    day_date_surface = font_medium.render(day_date, True, (255, 255, 255))
    day_date_rect = day_date_surface.get_rect(center=(time_tile_rect[0] + time_tile_rect[2] // 2, time_tile_rect[1] + time_height + font_medium.get_height() - SMALL_FONT))
    screen.blit(day_date_surface, day_date_rect)

    if seconds != seconds_new:
        seconds = seconds_new
        seconds_surface = font_small.render(seconds, True, (255, 255, 255))
        seconds_rect = seconds_surface.get_rect(bottomright=(time_tile_rect[0] + time_tile_rect[2] - padding, time_tile_rect[1] + time_tile_rect[3] - padding))
        screen.blit(seconds_surface, seconds_rect)

# Function to draw the weather tile
def draw_weather_tile():
    """Draws the weather tile."""
    global weather_data
    iconId = "02d"
    if weather_data:
        main = weather_data["main"]
        weather = weather_data["weather"][0]
        wind = weather_data["wind"]
        temp_c = round(main["temp"] - 273.15, 1)
        weather_lines = [
            f"    {temp_c}°C", ""
        ]
        small_lines = [
             f"{weather['description']}",
            f"Humidity: {main['humidity']}%"
        ]
        iconId = weather['icon']
        draw_tile(weather_tile_rect, (20, 138, 186), weather_lines, font_large)
        
    else:
        weather_lines = ["No data", "Check API", "Connection?"]
        draw_tile(weather_tile_rect, (20, 138, 186), weather_lines, font_medium)
    
    if weather_data:
        icon_URL = f"https://openweathermap.org/img/wn/{iconId}@2x.png"
        
        response = requests.get(icon_URL)
        image_file = io.BytesIO(response.content)
        
        icon_radius = 100
        icon_x = weather_tile_rect[0] + padding
        icon_y = weather_tile_rect[1] + (weather_tile_rect[3] // 2)
        
        icon_surface = pygame.image.load(image_file).convert_alpha()
        icon_surface = pygame.transform.scale(icon_surface, (icon_radius, icon_radius))
        screen.blit(icon_surface, (icon_x - padding, icon_y-icon_radius))  # center it like the circle

        text_rect_width = weather_tile_rect[2] - 3 * (icon_radius + padding)
        text_rect = pygame.Rect(icon_x + icon_radius + padding, weather_tile_rect[1] + padding, text_rect_width, weather_tile_rect[3] - 2 * padding)
        
        tile_center_y = weather_tile_rect[1] + weather_tile_rect[3] // 2
        temp_text_height = font_large.get_height()
        start_y = tile_center_y

        for idx, line in enumerate(small_lines):
            text_surface = font_small.render(line, True, (255, 255, 255))
            text_rect = text_surface.get_rect(
                midtop=(weather_tile_rect[0] + weather_tile_rect[2] // 2, start_y + idx * (font_small.get_height() + 5))
            )
            screen.blit(text_surface, text_rect)
    
    update_weather = False


def draw_todo_tile():
    """Draws the todo tile."""
    global tasks
    heading_surface = font_medium.render("TO-DO", True, (255, 255, 255))
    heading_rect = heading_surface.get_rect(center=(todo_tile_rect[0] + todo_tile_rect[2] // 2, todo_tile_rect[1] + 20 + padding))
    pygame.draw.rect(screen, (19, 140, 139), todo_tile_rect, border_radius=12)
    screen.blit(heading_surface, heading_rect)

    if tasks:
        lines = []
        for task in tasks:
            if task['isChecked']:
                lines.append(f"☑ {task['taskText']}")
            else:
                lines.append(f"☐ {task['taskText']}")
        # adjust text area to start below the heading
        text_rect = pygame.Rect(
            todo_tile_rect[0],
            heading_rect.bottom + 10,
            todo_tile_rect[2],
            todo_tile_rect[3] - (heading_rect.height + 10)
        )
        draw_tile(text_rect, (19, 140, 139), lines, font_toDo, align="left")  # transparent background for text
    else:
        text_rect = pygame.Rect(
            todo_tile_rect[0],
            heading_rect.bottom + 10,
            todo_tile_rect[2],
            todo_tile_rect[3] - (heading_rect.height + 10)
        )
        draw_tile(text_rect, (19, 140, 139), ["No tasks pending."], font_toDo)
        update_ToDo = False


def load_data():
    """Load data from the JSON file."""
    global API_URL, LAT, LON, tasks, last_modified_time, API_KEY
    try:
        # Get the last modified time of the file
        current_modified_time = os.path.getmtime(data_file_path)

        # Check if the file has been modified since the last load
        if current_modified_time > last_modified_time:
            logging.info("Data file has been updated. Reloading...")
            with open(data_file_path, 'r') as f:
                data = json.load(f)
            last_modified_time = current_modified_time
            API_KEY = data.get('apiKey', "")
            LAT = data.get('latitude', 0)
            LON = data.get('longitude', 0)
            tasks = data.get('tasks', [])
            API_URL = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&APPID={API_KEY}"
            return True  # return true if data is updated
        else:
            return False
    except FileNotFoundError:
        logging.warning(f"{data_file_path} not found.  Starting with default configuration.")
        return False
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {data_file_path}.  Using default configuration.")
        return False
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return False

def reload_config_and_data():
    """Function to reload configuration and data."""
    global weather_data, last_weather_update, data_loaded, API_KEY
    logging.info("Reloading configuration and data.")

    if load_data():  # load data and check if updated
        if API_KEY:
            weather_data = fetch_weather()  # fetch weather
            last_weather_update = time.time()
        else:
            weather_data = None
        draw_weather_tile()
        draw_todo_tile()
        pygame.display.flip()  # update display
        data_loaded = True



# Load initial data
load_data()
if API_KEY:  # changed
    weather_data = fetch_weather()
    last_weather_update = time.time()
    data_loaded = True
else:
    logging.info("API key not found on initial load.  Waiting for update.")

# Flask endpoint to serve the main dashboard page
@app.route('/')
def index():
    """Serves the main dashboard page (index.html)."""
    return render_template('index.html')  # Make sure index.html is in the same directory as this script

# Flask endpoint to get the current configuration
@app.route('/get_config', methods=['GET'])
def get_config():
    """
    Handles the GET request to retrieve the configuration data.
    Loads data from config.json and returns it as JSON.
    """
    global config_data
    resetConfig()
    try:
        with open(data_file_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        logging.warning(f"{data_file_path} not found.  Returning empty config.")
        resetConfig()
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {data_file_path}.  Returning empty config.")
        resetConfig()
    except Exception as e:
        logging.error(f"Error in /get_config: {e}")
        return jsonify({'error': f'Error fetching configuration: {e}'}), 500

    return jsonify(config_data)

# Flask endpoint to receive updates (e.g., from a web form)
@app.route('/update_config', methods=['POST'])
def update_config():
    """Handles the POST request to update configuration data."""
    global API_URL, LAT, LON, tasks, last_modified_time, API_KEY, config_data, update_weather
    
    update_weather = True
    update_ToDo = True

    try:
        # Check if the request contains JSON data
        if request.content_type == 'application/json':
            data = request.get_json()
            logging.info(f"Received data from /update_config: {data}")
        else:
            data = request.form # fallback to form data.
            logging.info(f"Received form data from /update_config: {data}")
            if not data:
                return jsonify({'success': False, 'message': 'No JSON or form data provided'}), 400

        # Load the current config.json
        if os.path.exists(data_file_path):
            try:
                with open(data_file_path, 'r') as f:
                    config_data = json.load(f)
            except Exception as e:
                logging.error(f"Error in file open: {e}")
                resetConfig()
        else:
            resetConfig()
            logging.info(f"file not found")

        # Update the config data with the new values from the POST request
        config_data['apiKey'] = data.get('apiKey', config_data.get('apiKey', ""))  # Use existing or default
        config_data['latitude'] = data.get('latitude', config_data.get('latitude', 0))
        config_data['longitude'] = data.get('longitude', config_data.get('longitude', 0))
        config_data['tasks'] = data.get('tasks', config_data.get('tasks', []))

        # update the global variables
        API_KEY = config_data['apiKey']
        LAT = config_data['latitude']
        LON = config_data['longitude']
        tasks = config_data['tasks']
        API_URL = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&APPID={API_KEY}"


        # Write the updated config data back to config.json
        with open(data_file_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        last_modified_time = os.path.getmtime(data_file_path)  # update last modified time

        # force reload
        reload_config_and_data()  # call the reload function

        return jsonify({'success': True, 'message': 'Configuration updated successfully!'})
    except Exception as e:
        logging.error(f"Error in /update_config: {e}")
        return jsonify({'success': False, 'message': f'Failed to update configuration: {e}'}), 500



def start_flask():
    """Starts the Flask application."""
    app.run(host='0.0.0.0', port=5000, debug=False)  # Change port if needed.  Set debug=False for production

# Create a thread for the Flask server
flask_thread = Thread(target=start_flask)
flask_thread.daemon = True  # So it doesn't block program exit
flask_thread.start()

# Main loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()

    screen.fill((0, 0, 0))

    # draw time tile always
    draw_time_tile()
    draw_quote_bar()
    
    # Draw the weather tile
    if update_weather:
        weather_data = fetch_weather()
        last_weather_update = time.time()
        draw_weather_tile()
    # Draw the todo tile
    if update_ToDo:
        draw_todo_tile()

    # Update weather data every update_interval seconds
    if time.time() - last_weather_update > update_interval and API_KEY: # added check for API_KEY
        weather_data = fetch_weather()
        last_weather_update = time.time()
        update_weather = True

    pygame.display.flip()
    clock.tick(1)