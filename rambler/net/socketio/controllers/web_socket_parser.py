from collections import defaultdict
from Rambler import outlet

class WebSocketParser(object):
  log = outlet('LogService')
  
  def __init__(self):
    self.reset()
    
    self.opcodeHandles = {
      '1': self.text_handler,
      '8': self.close_handler,
      '9': self.ping_handler
    }
    self.expect('Opcode', 2, self.processPacket)
    
    self.listeners_by = defaultdict(list)


  def on(self, event, listener):
    self.listeners_by[event].append(listener)
    
  def emit(self, event, *args):

    if self.listeners_by[event]:
      for listener in  self.listeners_by[event]:
        listener(*args)
    else:
      self.log.debug('%s event received with no listeners', event)

    
  def on_data(self, data, mask):
    self.finish(mask, data)
    
  def on_mask(self, mask, length):
    self.expect('Data', length, self.on_data, mask)
    
  def on_64bit_length(self, data):
    if (util.unpack(data.slice(0, 4)) != 0):
      self.error('packets with length spanning more than 32 bit is currently not supported');
      return
    self.expect_data(util.unpack(data))

  def expect_data(self, length):
    if (self.state_masked):        
      self.expect('Mask',4, self.on_mask, length)
    else:
      self.expect('Data', length, self.finish, None) 
    
  def decode_length(self, data):
    # decode length
    firstLength = data[1] & 0x7f
    if firstLength < 126:
      self.expect_data(firstLength)
    elif (firstLength == 126):
      self.expect('Length', 2, lambda data: self.expect_data(util.unpack(data)))
    elif (firstLength == 127):
      self.expect('Length', 8, self.on_64_bit_length)  

  def finish_text(self, mask, data):
    self.currentMessage += self.unmask(mask, data)
    if self.state_lastFragment:
      self.emit('data', self.currentMessage)
      self.currentMessage = ''
    self.endPacket()
  
  def text_handler(self, data):
    self.finish = self.finish_text
    self.decode_length(data)
           
  def close_handler(self, data):
    self.emit('close')
    self.reset()

  def finish_ping(self, mask, data):
    self.emit('ping', self.unmask(mask, data))
    self.endPacket()
    
  def ping_handler(self, data):
    # ping
    if self.state_lastFragment == False:
      self.error('fragmented ping is not supported');
      return
      
    self.finish = finish_ping
    self.decode_length(data)


  #/**
  # * Add new data to the parser.
  # *
  # * @api public
  # */

  def add(self, data):
    if self.expectBuffer is None:
      self.addToOverflow(data)
      return

    toRead = min(len(data), len(self.expectBuffer) - self.expectOffset)
    self.expectBuffer[self.expectOffset:] = data[:toRead]

    self.expectOffset += toRead
    if toRead < len(data):
      # at this point the overflow buffer shouldn't at all exist
      self.overflow = bytearray(data[toRead:])
      
    
    if self.expectOffset == len(self.expectBuffer):
      bufferForHandler = self.expectBuffer
      self.expectBuffer = None
      self.expectOffset = 0
      self.expectHandler(bufferForHandler, *self.expectArgs)

  #/**
  #* Adds a piece of data to the overflow.
  #*
  #* @api private
  #*/

  def addToOverflow(self, data):
    if self.overflow is None: 
      self.overflow = data
    else:
      self.overflow = bytearray(self.overflow + data)

  #/**
  #* Waits for a certain amount of bytes to be available, then fires a callback.
  #*
  #* @api private
  #*/

  def expect(self, what, length, handler, *args):
    self.expectBuffer = bytearray(length)
    self.expectOffset = 0
    self.expectHandler = handler
    self.expectArgs = args
    if self.overflow is not None:
      toOverflow = self.overflow
      self.overflow = None
      self.add(toOverflow);



  #/**
  #* Start processing a new packet.
  #*
  #* @api private
  #*/

  def processPacket(self, data):
    if (data[0] & 0x70) != 0: 
      self.error('reserved fields must be empty')
    
    self.state_lastFragment = (data[0] & 0x80) == 0x80
    self.state_masked = (data[1] & 0x80) == 0x80
    opcode = data[0] & 0xf
    
    if (opcode == 0):
      #// continuation frame
      self.state_opcode = self.state_activeFragmentedOperation
      if not (self.state_opcode == 1 or self.state_opcode == 2):
        self.error('continuation frame cannot follow current opcode')
        return
    else:
      self.state_opcode = opcode;
      if self.state_lastFragment == False:
        self.state_activeFragmentedOperation = opcode
    #import pdb; pdb.set_trace()
    handler = self.opcodeHandles.get(str(self.state_opcode))
    if handler is None: 
      self.error('no handler for opcode ' + self.state_opcode)
    else: 
      handler(data)


  #/**
  #* Endprocessing a packet.
  #*
  #* @api private
  #*/

  def endPacket(self):
    self.expectOffset  = 0
    self.expectBuffer  = None
    self.expectHandler = None
    if self.state_lastFragment and self.state_opcode == self.state_activeFragmentedOperation:
      # end current fragmented operation
      self.state_activeFragmentedOperation = None
    
    self.state_lastFragment = False
    self.state_opcode =  self.state_activeFragmentedOperation if self.state_activeFragmentedOperation is not None else 0
    self.state_masked = False
    self.expect('Opcode', 2, self.processPacket);  


  #/**
  #* Reset the parser state_
  #*
  #* @api private
  #*/

  def reset(self): 
    self.state_activeFragmentedOperation = None
    self.state_lastFragment = False
    self.state_masked = False
    self.state_opcode = 0
    
    
    self.expectOffset = 0
    self.expectBuffer = None
    self.expectHandler = None
    self.expectArgs = []
    self.overflow = None
    self.currentMessage = ''


  #/**
  #* Unmask received data.
  #*
  #* @api private
  #*/

  def unmask(self, mask, buf):
    if mask is not None:
      for i in range(len(buf)):
        buf[i] ^= mask[i % 4];
            
    return buf.decode("utf-8", "replace") if buf is not None else ''


  #/**
  #* Handles an error
  #*
  #* @api private
  #*/

  def error(self, reason):
    self.reset()
    self.emit('error', reason)
    return self

