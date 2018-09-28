from bluepy.btle import UUID, Peripheral, ADDR_TYPE_RANDOM, DefaultDelegate
import btle
import argparse
import time
import struct
import binascii
import sys

# Please see # Ref https://nordicsemiconductor.github.io/Nordic-Thingy52-FW/documentation
# for more information on the UUIDs of the Services and Characteristics that are being used
def Nordic_UUID(val):
    """ Adds base UUID and inserts value to return Nordic UUID """
    return UUID("EF68%04X-9B35-4933-9B10-52FFA9740042" % val)

def Microbit_UUID(val):
    """ Adds base UUID and inserts value to return MicroBit UUIDs """
    return UUID("E95D%04X-251D-470A-A062-FA1922DFA9A8" % val)

# Definition of all UUID used by Thingy
CCCD_UUID = 0x2902

ACCEL_SERVICE   = 0x0753
ACCEL_DATA      = 0xCA4B
ACCEL_PERIOD    = 0xFB24
MAGNETO_SERVICE = 0xF2D8
MAGNETO_DATA    = 0xFB11
MAGNETO_PERIOD  = 0x386C
MAGNETO_BEARING = 0x9715
BTN_SERVICE     = 0x9882
BTN_A_STATE     = 0xDA90
BTN_B_STATE     = 0xDA91
IO_PIN_SERVICE  = 0x127B
IO_PIN_DATA     = 0x8D00
IO_AD_CONFIG    = 0x5899
IO_PIN_CONFIG   = 0xB9FE
IO_PIN_PWM      = 0xD822
LED_SERVICE     = 0xD91D
LED_STATE       = 0x7B77
LED_TEXT        = 0x93EE
LED_SCROLL      = 0x0D2D
TEMP_SERVICE    = 0x6100
TEMP_DATA       = 0x9250
TEMP_PERIOD     = 0x1B25

# Notification handles used in notification delegate

class TemperatureService():
    """
    Temperature Service module.
    """
    svcUUID = Microbit_UUID(TEMP_SERVICE)
    dataUUID = Microbit_UUID(TEMP_DATA)

    def __init__(self, periph):
        self.periph = periph
        self.service = None
        self.data = None

    def enable(self):
        """ Enables the class by finding the service and its characteristics. """
        if self.service is None:
            self.service = self.periph.getServiceByUUID(self.svcUUID)
        if self.data is None:
            self.data = self.service.getCharacteristics(self.dataUUID)[0]

    def read(self):
        """ Returns the temperature in degrees Celcius """
        val = ord(self.data.read())
        return val


class AcceleratorService():
    """
    Accelerator Service module.
    """
    svcUUID = Microbit_UUID(ACCEL_SERVICE)
    dataUUID = Microbit_UUID(ACCEL_DATA)

    def __init__(self, periph):
        self.periph = periph
        self.service = None
        self.data = None

    def enable(self):
        """ Enables the class by finding the service and its characteristics. """
        if self.service is None:
            self.service = self.periph.getServiceByUUID(self.svcUUID)
        if self.data is None:
            self.data = self.service.getCharacteristics(self.dataUUID)[0]

    def read(self):
        """ Returns the X/Y/Z axis acceleration.
        read() will returns 3 little-endian signed shorts """
        accel_data = self.data.read()
        (x,y,z) = struct.unpack("<hhh", accel_data)
        return (x,y,z)



class ButtonsService():
    """
    Buttons Service module.
    """
    svcUUID = Microbit_UUID(BTN_SERVICE)
    dataUUID_btnA = Microbit_UUID(BTN_A_STATE)
    dataUUID_btnB = Microbit_UUID(BTN_B_STATE)

    def __init__(self, periph):
        self.periph = periph
        self.service = None
        self.dataA = None
        self.dataB = None

    def enable(self):
        """ Enables the class by finding the service and its characteristics. """
        if self.service is None:
            self.service = self.periph.getServiceByUUID(self.svcUUID)
        if self.dataA is None:
            self.dataA = self.service.getCharacteristics(self.dataUUID_btnA)[0]
        if self.dataB is None:
            self.dataB = self.service.getCharacteristics(self.dataUUID_btnB)[0]

    def read_btnA(self):
        """ Returns the state of the A button """
        return ord(self.dataA.read())

    def read_btnB(self):
        """ Returns the state of the B button """
        return ord(self.dataB.read())

    def read(self):
        """ return both buttons """
        return (self.read_btnA(), self.read_btnB())


class Microbit(Peripheral):
    """
    Microbit module. Instance the class.
    The addr of your device has to be known, or can be found by using the hcitool command line 
    tool, for example. Call "> sudo hcitool lescan" and your Thingy's address should show up.
    """
    def __init__(self, addr, iface=None):
        Peripheral.__init__(self, addr, addrType=ADDR_TYPE_RANDOM, iface=iface)

        self.temperature = TemperatureService(self)
        self.accelerator = AcceleratorService(self)
        self.buttons = ButtonsService(self)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mac_address', action='store', help='MAC address of BLE peripheral')
    parser.add_argument('-n', action='store', dest='count', default=1,
                            type=int, help="Number of times to loop data")
    parser.add_argument('-t',action='store',type=float, default=1.0, help='time between polling')
    parser.add_argument('--temperature', action="store_true",default=False)
    parser.add_argument('--accelerator', action="store_true",default=False)
    parser.add_argument('--buttons', action="store_true",default=False)
    parser.add_argument('--security', choices=["no-pairing","just-works","passkey","low","medium","high"],
            default="no-pairing")
    parser.add_argument('--pair', action="store_true",default=False)
    parser.add_argument("--interface", type=int, default=0)
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()

    services_requested = args.temperature or args.accelerator or args.buttons
    if args.pair and services_requested:
        sys.exit("error: --pair can not be combined with other services (e.g --buttons)")
    if not args.pair and not services_requested:
        sys.exit("no action requested (e.g --pair or --temperature/--accelerator/--buttons), aborting.")

    if args.debug:
        btle.Debugging = True

    if args.pair:
        p = btle.Peripheral(args.mac_address, btle.ADDR_TYPE_RANDOM, iface=args.interface)
        try:
            p.unpair()
        except btle.BTLEException as e:
            if e.code == btle.BTLEException.DISCONNECTED and e.estat == 6:
                print "unpair failed: not-paired (which is OK)"
                pass
            else:
                raise
        p.disconnect()
        p = btle.Peripheral(args.mac_address, btle.ADDR_TYPE_RANDOM, iface=args.interface)
        p.pair()

        # If we got here - pairing succeeded
        print("Paired.")
        sys.exit(0)


    print('Connecting to ' + args.mac_address)
    microbit = Microbit(args.mac_address)

    print('Setting security')
    if args.security in ['low','no-pairing']:
        microbit.setSecurityLevel("low")
    elif args.security in ['just-works','medium']:
        microbit.setSecurityLevel("medium")
    else:
        sys.exit("error: microbit with Passkey security mode is not currently supported in this program")

    try:
        # Enabling selected sensors
        print('Enabling selected sensors...')

        if args.temperature:
            microbit.temperature.enable()
        if args.accelerator:
            microbit.accelerator.enable()
        if args.buttons:
            microbit.buttons.enable()
        
        counter=1
        while True:
            if args.temperature:
                print("Temperature: %dC" % microbit.temperature.read())
            if args.accelerator:
                (x,y,z) = microbit.accelerator.read()
                print("Accelerator: x: {:05d}   y: {:05d}   z: {:05d}".format(x,y,z))
            if args.buttons:
                (a, b) = microbit.buttons.read()
                print("buttons: A: %d   B: %d" % (a,b))

            if counter >= args.count:
                break
            
            counter += 1
            microbit.waitForNotifications(args.t)

    finally:
        microbit.disconnect()
        del microbit


if __name__ == "__main__":
    main()
