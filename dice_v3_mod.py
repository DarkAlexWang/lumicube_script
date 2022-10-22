numbers = {
    1: [[black, black, black, black, black, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, red, red, black, black, black],
        [black, black, black, red, red, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, black, black, black, black, black]],
    2: [[black, black, black, black, black, black, black, black],
        [black, red, red, black, black, black, black, black],
        [black, red, red, black, black, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, black, black, black, black, black],
        [black, black, black, black, black, red, red, black],
        [black, black, black, black, black, red, red, black],
        [black, black, black, black, black, black, black, black]],
    3: [[red, red, black, black, black, black, black, black],
                                   [red, red, black, black, black, black, black, black],
                                   [black, black, black, black, black, black, black, black],
                                   [black, black, black, red, red, black, black, black],
                                   [black, black, black, red, red, black, black, black],
                                   [black, black, black, black, black, black, black, black],
                                   [black, black, black, black, black, black, red, red],
                                   [black, black, black, black, black, black, red, red]],
    4: [[black, black, black, black, black, black, black, black],
                                   [black, red, red, black, black, red, red, black],
                                   [black, red, red, black, black, red, red, black],
                                   [black, black, black, black, black, black, black, black],
                                   [black, black, black, black, black, black, black, black],
                                   [black, red, red, black, black, red, red, black],
                                   [black, red, red, black, black, red, red, black],
                                   [black, black, black, black, black, black, black, black]],
    5: [[red, red, black, black, black, black, red, red],
                                   [red, red, black, black, black, black, red, red],
                                   [black, black, black, black, black, black, black, black],
                                   [black, black, black, red, red, black, black, black],
                                   [black, black, black, red, red, black, black, black],
                                   [black, black, black, black, black, black, black, black],
                                   [red, red, black, black, black, black, red, red],
                                   [red, red, black, black, black, black, red, red]],
    6: [[black, black, black, black, black, black, black, black],
                                   [red, red, black, red, red, black, red, red],
                                   [red, red, black, red, red, black, red, red],
                                   [black, black, black, black, black, black, black, black],
                                   [black, black, black, black, black, black, black, black],
                                [red, red, black, red, red, black, red, red],
                                   [red, red, black, red, red, black, red, red],
                                   [black, black, black, black, black, black, black, black]],
}

def print_number(number,panel):
    global numbers
    display.set_panel(panel, numbers[number])
    
def shake(count):
    dices = []
    for dice in range(count):
        dices.append(random.randint(1,6))
    return dices
    
def roll_dice(count = 1, interval = 0.1):
    
    for run in range(10, random.randint(20,50), 1):
        yield shake(count)
        time.sleep(interval)
    return shake(count)

import asyncio
def say(result):
   time.sleep(1)
   speaker.say(result)
    
async def blink(faces, roll):
    for blink_step in range(10):
        if blink_step % 2 == 0:
            for face, dice in zip(faces, roll):
                print_number(dice, face)
        else:
            display.set_all(black)
        await asyncio.sleep(0.5)
    
async def display_result(faces, roll):
    await asyncio.gather(
        asyncio.to_thread(say, sum(roll)),
        blink(faces, roll)
    )
   
                               
# hello & instructions on panel & lcd screen
screen.draw_rectangle(0, 0, 320, 240, black)
screen.write_text(0, 30, "LumiDice", 2, white)
screen.write_text(0, 80, "TOP     throw a die", 1, white)
screen.write_text(0, 120, "MIDDLE  throw two dice", 1, white)
screen.write_text(0, 160, "BOTTOM  throw three dice", 1, white)
display.scroll_text("LumiDice", colour = orange, background_colour=black, speed=0.5)
display.scroll_text("See LCD screen for instructions", colour=red, background_colour=black, speed=1)

#wait for a button to be pressed
while True:
    action = buttons.get_next_action(9999999)
    display.set_all(black)
    #top button - top panel   
    if action == "top":
        faces = ["top"]
    #middle button - left & right panels
    elif action == "middle":
        faces = ["left", "right"]
    #bottom button - all three panels
    elif action == "bottom":
        faces = ["top", "left", "right"]
   
    for roll in roll_dice(len(faces)):
        for face, dice in zip(faces, roll):
            print_number(dice, face)
    
    asyncio.run(display_result(faces, roll))

      