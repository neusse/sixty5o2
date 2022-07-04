import serial
import asyncio

SerialPort = require('serialport')
Readline = require('@serialport/parser-readline')
fs = require('fs')
EventEmitter = require('events')
class MyEmitter extends EventEmitter:


# Constants for events
START = 'start'
CHUNK_SUCCESS = 'chunkSuccess'
CHUNK_FAILURE = 'chunkFailure'
EOF = 'eof'

# Constants for serial port communication
SERIAL_ERROR = 'error'
SERIAL_DATA = 'data'

# Protocol constants
PROTOCOL_OK = 'k'
PROTOCOL_FAILURE = 'f'

# JSON config file for all connection related details
CONFIG_FILE_NAME = '.sender_config.json'

# Application timeout values
startTimeout = 2000
byteTimeout = 0  # not needed, data transfer is stable w/o positive values
chunkTimeout = 0  # not needed, since we wait for Arduino ack after every chunk anyways

# get a serial connection with default params


def connectSerial(config, tty):
  connection = SerialPort(tty | | config.tty, :
      baudRate: config.baudrate,
      databits: config.databits,
      parity: config.parity,
      stopbits: config.stopbits
  )

  # Open errors will be emitted as an error event
  connection.on(SERIAL_ERROR, (err):
    console.log('Error on read: ', err.message)
  )

  return connection


# establish a parser for data read from Arduino
def establishParser(connection, emitter):
    parser = Readline()
    connection.pipe(parser)

    parser.on(SERIAL_DATA, (data):
      response=data.toString().trim()
      if (response == PROTOCOL_OK):
        emitter.emit(CHUNK_SUCCESS)
       else if (response == PROTOCOL_FAILURE):
        emitter.emit(CHUNK_FAILURE)
       else:
        console.log('Arduino Response: ', response)

    )


# write a single byte to the serial connection
def sendByte(connection, char):
  connection.write(char, (err):
    if (err):
      return console.log('Error on write: ', err.message)

  )


# write a chunk of bytes to the serial connection including checksum
def sendChunk(connection, data):
  idx = 0

  # both methods are destructive
  data = appendPadding(data)
  data = appendChecksum(data)

  base64 = data.toString('base64')

  # decimals = data.join('-')
  # console.log('Data: ', decimals)
  # console.log('Base64: ', base64)

  return Promise((res):
    setTimeout(():
      interval=setInterval(():
        if (idx == base64.length):
          clearInterval(interval)
          res()
         else:
          sendByte(connection, base64[idx])
          idx += 1, byteTimeout), chunkTimeout)
  )


# simple 1-byte checksum algorithm
def checkSum(data):
  cs = 0
  data.forEach((element):
    bin=element.toString(2)
    cs=(cs << 1) + parseInt(bin[bin.length - 1])
  )

  return cs


# appends checksum to given buffer
def appendChecksum(buf):
  return Buffer.concat([buf, Buffer.alloc(1, [checkSum(buf)])], 9)


# add 0x00 padding bytes to buffer of different length than 8 (potentially only the last)
# necessary, because otherwise the checksum will not be in the right place and
# the chunk will be requested forever
def appendPadding(buf):
  if (buf.length == 8):
    return buf
   else:
    return Buffer.concat([buf, Buffer.alloc((8 - buf.length), 0)], 8)
  


# reads a file from filesystem and async returns it as a buffer
def readFile(fileName):
  return Promise((res, rej):
    fs.readFile(fileName, (err, data):
      if (err): rej('Error while reading file: ' + fileName) 
      res(data)
    )
  )


# cut the given array / buffer into chunks of given size
def inGroupsOf(ary, size):
  result = []
  for (i = 0; i < ary.length; i += size):
    chunk = ary.slice(i, i + size)
    result.push(chunk)
  

  return result


# simple index constructor function
def Index(m):
  idx = 0
  max = m - 1

  get = ():
    return idx
  

  increase = ():
    if (idx >= max):
      return null
    else:
      idx += 1

      return idx
    
  return:
    get,
    increase
  


# registering all event handler functions
def establishEventHandlers(connection, index, chunks):
  myEmitter = MyEmitter()

  myEmitter.on(START, (connection, chunk):
    sendFirstChunk(connection, chunk)
  )

  myEmitter.on(CHUNK_SUCCESS, ():
    sendNextChunk(connection, index, chunks, myEmitter)
  )

  myEmitter.on(CHUNK_FAILURE, ():
    repeatChunk(connection, index, chunks, myEmitter)
  )

  myEmitter.on(EOF, ():
    quit(connection)
  )

  return myEmitter


# sends the very first chunk
def sendFirstChunk(connection, chunk):
  console.log('Sending chunk: 0')
  sendChunk(connection, chunk)


# increases index and sends next chunk
# emits EOF event, when no chunk is left
def sendNextChunk(connection, index, chunks, emitter):
  idx = index.increase()

  if (idx):
    console.log('Sending chunk: ', idx)
    sendChunk(connection, chunks[idx])
   else:
    console.log('No chunk left!')
    emitter.emit(EOF)
  


# gets current index and repeats the chunk sent before
def repeatChunk(connection, index, chunks, emitter):
  idx = index.get()

  if (idx):
    console.log('Repeating chunk: ', idx)
    sendChunk(connection, chunks[idx])
   else:
    emitter.emit(EOF)
  


# gracefully quits the program
def quit(connection):
  console.log('Data transferred successfully! Quitting.')

  connection.close()
  process.exit(0)


# main
def main():
(async ():
  inFileName = process.argv[2]
  tty = process.argv[3]

  if (!inFileName):
    console.log('No input file given!')
    process.exit(1)
  

  try:
    console.log('Reading input file: ', inFileName)
    inFile = await readFile(inFileName)
    console.log('Done.')
    chunks = inGroupsOf(inFile, 8)
    
    console.log('Loading config file...')
    config = JSON.parse(fs.readFileSync(CONFIG_FILE_NAME))

    console.log('Establishing connection...')
    connection = connectSerial(config, tty)

    index = Index(chunks.length)

    console.log('Establishing event handlers...')
    emitter = establishEventHandlers(connection, index, chunks)
    console.log('Done.')
  
    setTimeout(():
      console.log('Connected.')
      console.log('Establishing parser...')
      establishParser(connection, emitter)
      console.log('Ready to send data.')
      
      emitter.emit(START, connection, chunks[0])
    , startTimeout)
   catch(e):
    console.log(e)
    process.exit(1)
  



if __name__ == '__main__':
  main()
