from datetime import datetime

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
    
    response.headers['Upgrade'] = 'WebSocket'
    response.headers['Connection'] = 'Upgrade'
    response.headers['Sec-WebSocket-Origin'] = request.headers.get('Origin')
    
    response.status = '101 WebSocket Protocol Handshake'


    self.executing = True
    WebSocket.channels.add(self)
    
    self.delegate = delegate
    if hasattr(self.delegate, 'on_open'):
      self.delegate.on_open(self)
    

  @property
  def result(self):
    return self