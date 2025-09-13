import msgpack
import lz4.block

def unpack_packet(data: bytes):
    ver = int.from_bytes(data[0:1], 'big')
    cmd = int.from_bytes(data[1:3], 'big')
    seq = int.from_bytes(data[3:4], 'big')
    opcode = int.from_bytes(data[4:6], 'big')
    packed_len = int.from_bytes(data[6:10], 'big', signed=False)
    comp_flag = packed_len >> 24
    payload_length = packed_len & 0xFFFFFF
    payload_bytes = data[10:10 + payload_length]
    if comp_flag != 0:
        compressed_data = payload_bytes
        try:
            payload_bytes = lz4.block.decompress(compressed_data, uncompressed_size=255)
        except lz4.block.LZ4BlockError:
            return None
    payload = msgpack.unpackb(payload_bytes, raw=False)
    return {
        "ver": ver,
        "cmd": cmd,
        "seq": seq,
        "opcode": opcode,
        "payload": payload
    }

# ToDo: Add lz4 compression
def pack_packet(ver: int, cmd: int, seq: int, opcode: int, payload: dict):
    ver_b = ver.to_bytes(1, 'big')
    cmd_b = cmd.to_bytes(2, 'big')
    seq_b = seq.to_bytes(1, 'big')
    opcode_b = opcode.to_bytes(2, 'big')
    payload_bytes = msgpack.packb(payload)
    payload_len_b = len(payload_bytes).to_bytes(4, 'big')
    return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes
