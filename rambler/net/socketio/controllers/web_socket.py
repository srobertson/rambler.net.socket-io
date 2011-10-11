from datetime import datetime
from hashlib import sha1
import base64

from Rambler import outlet, component
class WebSocket(component('Operation')):
  """Streams an events to an open webrequest.
  
  Discussion: This component mimics the operation interface so that
  a coroutine can yield it. On init it is already executing
  therefore the Scheduler will not try to queue it to be started in it's Operation
  Queue. 
  """
  
  log = outlet('LogService')
  RunLoop = outlet('RunLoop')
  Parser = outlet('WebSocketParser')
  is_concurrent = True


  @classmethod
  def assembled(cls):
    cls.rebase()
    cls.channels = set()
    
  def __init__(self, wsgi, request, response, delegate):
    # We want avoid adding this operation to a queue, there's
    # no reason this operation should block other operations
    # from running.
    
    
    super(WebSocket, self).__init__()
    self.delegate = delegate
    self.parser = self.Parser()
    self.parser.on('data', self.on_data)
    self.parser.on('close', self.on_close)
    
    
    # calc key
    key = request.headers['sec-websocket-key'];  
    shasum = sha1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
    key = base64.b64encode(shasum.digest())
    
    headers = [
      'Upgrade: websocket', 
      'Connection: Upgrade', 
      'Sec-WebSocket-Accept: ' + key
     ]             

    port = request.environ['rambler.port']
    port.delegate = self
    
    port.debug = True
    port.write('HTTP/1.1 101 Switching Protocols\r\n')
    for header in headers:
      port.write('%s\r\n' % header)
    port.write('\r\n')
    self.port = port
    
    self.executing = True
    
    
  def emit(self, event, *args):
    # calls delgate.on_<event_name> if delegate defines the method and it's present

    method = getattr(self.delegate, 'on_' + event, None)
    if callable(method):
      method(self, *args)
      
  def write(self, data):
    self.port.write(self.frame(0x81, data))
    
  def frame(self, opcode, data):
    data_len = len(data)
    start_offset = 2
    second_byte = data_len
    
    if data_len > 65536:
      start_offset = 10
      second_byte = 127
   
    elif data_len > 125:
      start_offset = 4
      second_byte = 126
   
    output_buffer = bytearray(data_len + start_offset)
   
    output_buffer[0] = opcode;
    output_buffer[1] = second_byte
    output_buffer[start_offset:] = data
   
    if second_byte == 126:
      output_buffer[2] = data_len >> 8
      output_buffer[3] = data_len % 256;

    elif second_byte == 127:
      l = data_len
      for i in range(1,9):
        output_buffer[start_offset - i] = l & 0xff
        l >>= 8
       
    return output_buffer

  def on_close(self):
    self.port.close()
    
  def on_data(self, data):
    # called when the parser has decoded the web socket frame
    self.emit('message', data)

  def onRead(self, port, data):
    # Called when data arives from the socket
    self.parser.add(data)
    port.read(4096)

  def onWrite(self, port, bytesWritten):
    #print "I just wrote", bytesWritten
    pass

  def onClose(self, port):
    print "-- closed", port
    pass
    
  def onError(self, port, err):
    print "-- error", err
    pass

    
  @property
  def result(self):
    return self