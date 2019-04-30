from . import api
import gdb

import struct

inf = gdb.selected_inferior()

def _parse_u32(result):
  result = result.partition("=")[2]
  result = int(result, 0)
  return result

def interrupt_target():

  #FIXME: Figure this out somehow
  was_asynchronous = False

  result = gdb.execute("interrupt", to_string=True)
  return was_asynchronous

def continue_target(was_asynchronous):
  assert(was_asynchronous == False)
  #FIXME: Re-enable this code. However, we are currently affected by:
  #       https://stackoverflow.com/questions/10607021/c-thread-not-stopping-in-gdb-async-mode-using-user-defined-or-python-command-s/47781565#47781565
  #       https://stackoverflow.com/questions/47781852/gdb-not-stopping-with-interrupt-command-from-python-script
  #       So it's not possible to interrupt; so we can't continue either.
  if False:
    result = gdb.execute("c&" if was_asynchronous else "c", to_string=True)

def read(address, size, physical):
  #if physical:
  #  adddress |= 0x80000000
  old_state = interrupt_target()
  if size == 4:
    command = "print *(unsigned int*)0x%X" % (address)
    value = _parse_u32(gdb.execute(command, to_string=True))
    result = struct.pack("<I", value)
    #print("hack hack! read: %s -> 0x%X" % (command, value))
  else:
    #print("read: %d bytes from 0x%X" % (size, address))
    result = bytes(inf.read_memory(address, size))
  continue_target(old_state)
  return result

def write(address, data, physical):
  if physical:
    adddress |= 0x80000000
  value = bytes(data)
  old_state = interrupt_target()
  if len(data) == 4:
    command = "set *(unsigned int*)0x%X = 0x%X" % (address, struct.unpack("<I", data)[0])
    #print("hack hack! write: %s" % command)
    gdb.execute(command, to_string=True)
  else:
    #print("write: %d bytes to 0x%X" % (len(data), address))
    inf.write_memory (address, value)
  continue_target(old_state)

def call(address, stack, registers=None):

  #FIXME: This is quite horrible, and there's probably better ways

  argument_types = []
  argument_data = []

  assert(len(stack) % 4 == 0)
  argument_count = len(stack) // 4
  for i in range(argument_count):
    value = struct.unpack_from("<I", stack, i * 4)[0]
    argument_types += ["unsigned int"]
    argument_data += ["0x%X" % (value)]

  command = "call ((unsigned int(*)(%s))0x%X)(%s)" % (",".join(argument_types), address, ",".join(argument_data))

  old_state = interrupt_target()
  result = _parse_u32(gdb.execute(command, to_string=True))
  continue_target(old_state)

  # Some magic with `call` using:
  # gdb.execute (command [, from_tty [, to_string]])
  # Maybe?
  out_registers = {}
  out_registers['eax'] = result
  return out_registers

api.read = read
api.write = write
api.call = call
