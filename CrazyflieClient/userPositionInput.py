# Keylogger import
import termios, fcntl, os, sys

# Callback import
#import logging

# sleep import
import time

# Enumerator import
from enum import Enum

# Store initial values, needed in order to restore settings after function call.
fd = sys.stdin.fileno()
oldterm = termios.tcgetattr(fd)
newattr = termios.tcgetattr(fd)
newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, newattr)
oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

class Action(Enum):
    increaseX = 1
    decreaseX = 2
    increaseY = 3
    decreaseY = 4
    increaseZ = 5
    decreaseZ = 6
    increaseYaw = 7
    decreaseYaw = 8
    changeQuad = 9
    killQuads = 10

class CoordinateHandler(object):
    """
    Object that stores a callback function for the setpoint manipulation.
    """
    def __init__(self):
        self.callbacks = []
    def subscribe(self, callback):
        self.callbacks.append(callback)
    def fire(self, yaw = 0, posX = 0, posY = 0, posZ = 0, quadnumber = 0, kill = 0):
        for fn in self.callbacks:
            fn(yaw, posX, posY, posZ, quadnumber, kill)

class SetpointManipulator():

    def __init__(self, cb):

        print "Callback registered."
        self._register_callback(callback_coords = cb)

        print "Setpoint manipulating activated."
        self._start_keylogging()

    def _get_action_from_key_press(self):
        """
        'e'   -   increase yaw
        'q'   -   decrease yaw
        'w'   -   increase X
        's'   -   decrease X
        'd'   -   increase Y
        'a'   -   decrease Y
	    'r'   -   increase Z
        'f'   -   decrease Z
        'c'   -   changeQuad
        'k'   -   killQuads
        """
        while 1:
            # The try handles events when there is no key pressed. In that case the
            # function immediately tries to detect a key press again.
            try:
                # Read in the last pressed key signature.
                c = sys.stdin.read(1)
                # Map the key signature to an action and return it.
                if c == 'e':
                    return Action.increaseYaw
                if c == 'q':
                    return Action.decreaseYaw
                if c == 'w':
                    return Action.increaseX
                if c == 's':
                    return Action.decreaseX
                if c == 'd':
                    return Action.increaseY
                if c == 'a':
                    return Action.decreaseY
                if c == 'r':
                    return Action.increaseZ
                if c == 'f':
                    return Action.decreaseZ
                if c == 'c':
                    return Action.changeQuad
                if c == 'k':
                    return Action.killQuads
            except IOError: pass

    def _start_keylogging(self):
        """
            Function that continuously checks the keyboard to detect
            when the user presse a key which prompts the execution of a
            callback function.
        """
        try:
	    deg_inc = 30
            increment = 0.1
            quad_inc  = 1
            while 1:
                # print "Waiting for a key to be pressed ... "
                action = self._get_action_from_key_press()
                if action is Action.increaseYaw:
                    self.ch.fire(yaw =+ deg_inc) 
                elif action is Action.decreaseYaw:
                    self.ch.fire(yaw =- deg_inc)
                elif action is Action.increaseX:
                    self.ch.fire(posX =+ increment) 
                elif action is Action.decreaseX:
                    self.ch.fire(posX =- increment) 
                elif action is Action.increaseY:
                    self.ch.fire(posY =+ increment) 
                elif action is Action.decreaseY:
                    self.ch.fire(posY =- increment) 
                elif action is Action.increaseZ:
                    self.ch.fire(posZ =+ increment) 
                elif action is Action.decreaseZ:
                    self.ch.fire(posZ =- increment) 
                elif action is Action.changeQuad:
                    self.ch.fire(quadnumber =+ quad_inc)
                elif action is Action.killQuads:
                    self.ch.fire(kill = 1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

    def _register_callback(self, callback_coords):
        """ Links the actions to callback functions."""
        self.ch = CoordinateHandler()
        self.ch.subscribe(callback_coords)
