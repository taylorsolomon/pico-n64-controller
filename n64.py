import rp2
from machine import Pin
from rp2 import PIO, asm_pio
import utime

# The PIO Output Shift Register is 32 bits, always. If we store 8 bits in it at a time, 
# We gotta shift those bits to the left all the way, so they're the most significant bits.
# This function bitshifts our byte over to the right place.
def masked_osr_byte(byte):
    return byte << 24

@asm_pio(in_shiftdir=PIO.SHIFT_LEFT, out_shiftdir=PIO.SHIFT_LEFT, autopull=True, pull_thresh=8, sideset_init=(PIO.OUT_HIGH))
def N64_PIO():
    # Pull data from micropython into the PIO and stick it in the Output Shift Register (OSR)
    pull()
    # Set the pins to output mode
    set(pindirs, 1)      
    # Set the X scratch register to be used as our bit loop counter
    set(x, 7)            
    # Bytes to be used:
    # Ox00 - Controller init
    # 0x01 - Request data from controller
    # 
    # Bytes are looped through bit by bit to conform to the joybus protocol:
    #   - Bit is 0: 3us low, 1us high
    #   - Bit is 1: 1us low, 3us high
    # Console sends a stop bit, which is 1us low, 2us high
    # Controller sends a stop bit, which is 2us low, 2us high
    label("bitloop")
    # Pull one bit out of the OSR and store it in the Y Scratch register. Do nothing with it lol.
    out(y, 1)
    # Set line low for 1us. We use the .side() setting approach, since it helps us to time things out.
    jmp(y_dec, "bit_is_1")  .side(0)
    # if bit is 0, delay, then shift. We do a nop(), then delay 2 more cycles.
    nop()							 [2]
    jmp("shift")            
    label("bit_is_1")
    # if bit is 1, shift immediately
    nop()
    nop()					.side(1) [2]
    label("shift")
    nop()
    jmp(x_dec, "bitloop")   .side(1)
    
    # Send Close bit
    nop()
    nop()		            .side(0) [1]
    nop()                   .side(1)
    
    # Set pins to input mode so we can get data back.
    set(pindirs, 0)
    # Todo: Receive data
    nop()                            [7]

# State machine controlling PIO program.
sm = rp2.StateMachine(0, N64_PIO, freq=2000000, set_base=machine.Pin(19), sideset_base=machine.Pin(19))

print("Starting state machine...")
sm.active(1)
sm.put(masked_osr_byte(0x00))
utime.sleep(1)
sm.put(masked_osr_byte(0x01))
print("Stopping state machine...")
sm.active(0)