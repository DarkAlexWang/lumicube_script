# Modified by S. Morar

def draw_column(decimal_digit, x, colour):
    # Convert digit to four digit binary
    binary = list(format(decimal_digit, '04b'))
    # Start at the bottom with the least significant digit
    binary.reverse()
    leds = {}
    for i, value in enumerate(binary):
        # Set all the leds in a 2x2 square
        pixel = colour if value == '1' else black
        y = i * 2
        leds[x,   y  ] = pixel
        leds[x,   y+1] = pixel
        leds[x+1, y  ] = pixel
        leds[x+1, y+1] = pixel
    display.set_leds(leds)

def scrolling_clock():
    time_text = datetime.datetime.now().strftime("%H:%M")
    display.scroll_text(time_text, orange, speed=0.5)

def binary_clock():
    time_now = datetime.datetime.now()
    seconds = format(time_now.second, '02')
    minutes = format(time_now.minute, '02')
    hours   = format(time_now.hour,   '02')
    draw_column(int(hours[0]),    0, pink)
    draw_column(int(hours[1]),    2, pink)
    draw_column(int(minutes[0]),  4, purple)
    draw_column(int(minutes[1]),  6, purple)
    draw_column(int(seconds[0]),  8, cyan)
    draw_column(int(seconds[1]), 10, cyan)

def to_text(value):
    return str("{:.1f}".format(value))

def update_screen():
    time_text = datetime.datetime.now().strftime("%a %d %b %H:%M")
    text = ("" 
        + "     " + time_text + "\n\n"
        + "IP address: " + pi.ip_address() + "\n"
        + "CPU temp  : " + to_text(pi.cpu_temp()) + "\n"
        + "CPU usage : " + to_text(pi.cpu_percent()) + "\n"
        + "RAM usage : " + to_text(pi.ram_percent_used()) +"\n"
        + "Disk usage: " + to_text(pi.disk_percent()) + "\n")
    screen.write_text(10, 18, text, 1, white, black)
    
import datetime

# Starting brightness level
brightness = 50

function_index = 0
# Active functions that can be scrolled through with middle button
functions = (binary_clock,scrolling_clock)

button_pressed = ""
display.set_all(black)
screen.draw_rectangle(0, 0, 320, 240, black)
last_second = 0
while True:
    #Scroll through brightness level by steps of 2
    if buttons.top_pressed or button_pressed=="top":
        brightness += 2
        if brightness > 100:
            brightness = 100
    if buttons.bottom_pressed or button_pressed=="bottom":
        brightness -= 2
        if brightness < 0:
            brightness = 0
    display.brightness = brightness
    
    # Modify function index to run different code, based on the middle button press
    if buttons.middle_pressed or button_pressed=="middle":
        function_index += 1
        if function_index >= len(functions):
            function_index = 0
        display.set_all(black)
        
    # Run fuction based on current active index
    functions[function_index]()
    
    # Update LCD display once a second
    time_now = datetime.datetime.now()
    this_second = time_now.second
    if this_second != last_second:
        update_screen()
    last_second = this_second

    # Wait for button press event or time-out...    
    button_pressed = buttons.get_next_action(1/10)
