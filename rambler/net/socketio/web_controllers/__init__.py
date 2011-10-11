from Rambler import component, option, outlet

class SocketioController(component('WebController')):
  """
  Provides SocketIO (http://socket.io) support accross multiple channels.
  
  Use:
  Include the following code in your routes.py file to map the the SocketIO handshake
  
  #SocketIO GET /socket.io/1 maps to the SocketIO.handshake
  map.connect('/socket.io/{protocol}', controller="SocketIO", action="handshake")
  map.connect('/socket.io/{protocol}/{action}/{sid}', controller="SocketIO")
  
  >>> class Component(object):
  ...   socketio = outlet('SocketioController')
  ...   def assembled(self):
  ...     self.socketio.on('connection', self.on_connection)
  
  
  """
  heart_beat      = option('socket.io', 'heartbeat', 15)
  closing_timeout = option('socket.io', 'closing_timeout', 15)
  transports      = 'websocket'
  
  WebSocket = outlet('WebSocket')
  run_loop  = outlet('RunLoop')
  scheduler = outlet('Scheduler')
  
  @classmethod
  def assembled(cls):
    cls.rebase()
    cls.delegate = None
    
  def emit(self, event, *args):
    # calls delgate.on_<event_name> if delegate defines the method and it's present
    if self.delegate:
      method = getattr(self.delegate, 'on_' + event, None)
      if callable(method):
        self.scheduler.call(method,*args)
  

    
  
  def handshake(self):
    # Apps need to map this in their routes file

    sid = 1 
    response = "{sid}:{heartbeat}:{closing}:{transports}".format(
      sid=sid, 
      heartbeat=self.heart_beat,
      closing=self.closing_timeout,
      transports=self.transports)
      
    self.render(text=response)
    
    
  def websocket(self):

    ws = self.WebSocket(self, self.request, self.response,self)
    
    # TODO: fire on_connect here and handle the hand shake and heart beat
    ws.write('1::')
    self.run_loop.currentRunLoop().intervalBetweenCalling(max(5,self.heart_beat -5), self.beat, ws )
    
    # WebSocket implements the Operation interface. Specifically when 
    # inited it sets is_executing to true. Yielding it here to the scheduler will
    # keep the connection open w/o blocking the rest of the app. Neat eh?
    
    
    watcher = yield ws
    # Watcher will only return here when the connection is closed
    self.rendered = True
    
    
  def beat(self, ws):
    ws.write('2::')
    
  def on_message(self, socket, message):
    if message.startswith('1'):
      type,id,namespace = message.split(':')
      self.emit('connect', socket, id, namespace)
      socket.write(message.encode('utf8'))
    elif message.startswith('2'):
      #heartbeat update connection times
      pass
    elif message.startswith('3'):
      mtype,mid,endpoint,data = message.split(':')
      self.emit('message', socket, mid, endpoint, data)
    else:
      print '---->', message
