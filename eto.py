
import json
import torch
import numpy as np

with open('data/g.json', 'rb') as file:
    data = json.loads(file.read())

program_data = torch.tensor(data['Program'], dtype=torch.uint8)
character_data = torch.tensor(data['Character'], dtype=torch.uint8)

program_data = np.array(data['Program'])


## ops

def SEI(state, a, b): state['StatusRegister']['Interrupt'] = 1
def CLD(state, a, b): state['StatusRegister']['Decimal'] = 0

def Z_set(value):
    state['StatusRegister']['Zero'] = 1*(value == 0)

def N_set(value):
    state['StatusRegister']['Negative'] = 1*(value & 0x80 == 0x80)

def LDA(state, a, b): state['Accumulator'] = a; Z_set(a); N_set(a)
def LDX(state, a, b): state['X'] = a; Z_set(a); N_set(a)
def LDY(state, a, b): state['Y'] = a; Z_set(a); N_set(a)
def DEX(state, a, b): state['X'] = np.uint8(state['X'] - 1); Z_set(state['X']); N_set(state['X'])
def DEY(state, a, b): state['Y'] = np.uint8(state['Y'] - 1); Z_set(state['Y']); N_set(state['Y'])
def INY(state, a, b): state['Y'] = np.uint8(state['Y'] + 1); Z_set(state['Y']); N_set(state['Y'])
def INC(state, a, b): state['Memory'][a] += 1; Z_set(state['Memory'][a]); N_set(state['Memory'][a])

def BIT(state, a, b):
    result = np.uint8(state['Accumulator'] & a)
    Z_set(result)
    N_set(a)
    state['StatusRegister']['Overflow'] = (a >> 6) & 0x01

def CMP(state, a, b):
    result = state['Accumulator'] - a
    Z_set(result); N_set(result)
    if a <= state['Accumulator']:
        state['StatusRegister']['Carry'] = 1
    else:
        state['StatusRegister']['Carry'] = 0

def CPX(state, a, b):
    result = state['X'] - a
    Z_set(result); N_set(result)
    if a <= state['X']:
        state['StatusRegister']['Carry'] = 1
    else:
        state['StatusRegister']['Carry'] = 0

def CPY(state, a, b):
    result = np.uint8(state['Y'] - a)
    Z_set(result); N_set(result)
    if a <= state['Y']:
        state['StatusRegister']['Carry'] = 1
    else:
        state['StatusRegister']['Carry'] = 0

def ORA(state, a, b): state['Accumulator'] |= a; Z_set(state['Accumulator']); N_set(state['Accumulator'])
def EOR(state, a, b): state['Accumulator'] ^= a; Z_set(state['Accumulator']); N_set(state['Accumulator'])
def AND(state, a, b): state['Accumulator'] &= a; Z_set(state['Accumulator']); N_set(state['Accumulator'])

def STA(state, a, b): state['Memory'][a] = state['Accumulator']
def STX(state, a, b): state['Memory'][a] = state['X']
def TXA(state, a, b): state['Accumulator'] = state['X']; Z_set(state['Accumulator']); N_set(state['Accumulator'])

def TXS(state, a, b): state['StackRegister'] = state['X']

def BPL(state, a, b):
    if state['StatusRegister']['Negative'] == 0:
        state['ProgramCounter'] += np.int8(a)

def BCS(state, a, b):
    if state['StatusRegister']['Carry'] == 1:
        state['ProgramCounter'] += np.int8(a)

def BNE(state, a, b):
    if state['StatusRegister']['Zero'] == 0:
        state['ProgramCounter'] += np.int8(a)

def JMP(state, a, b):
    state['ProgramCounter'] = a

def JSR(state, a, b):
    # Stack is from range 0x0100-0x1FF and grows down from 0x0100 + 0xFD.
    pc_H = state['ProgramCounter'] >> 8
    pc_L = state['ProgramCounter'] & 0x00FF

    state['Memory'][state['StackZero'] + state['StackOffset']] = pc_H
    state['StackOffset'] -= 1
    state['Memory'][state['StackZero'] + state['StackOffset']] = pc_L
    state['StackOffset'] -= 1

    state['ProgramCounter'] = a

def RTS(state, a, b):
    state['StackOffset'] += 1
    pc_L = state['Memory'][state['StackZero'] + state['StackOffset']]
    state['StackOffset'] += 1
    pc_H = state['Memory'][state['StackZero'] + state['StackOffset']]

    state['ProgramCounter'] = (pc_H << 8) + pc_L


#-

def imm(state, data):
    return data

def imm2(state, data1, data2):
    return data2*0x0100 + data1

def indx(state, data):
    address = data + state['X']
    return state['Memory'][(address + 1)*0x0100 + address*data]

def indy(state, data):
    address = state['Memory'][data+1]*0x0100 + state['Memory'][data]
    return address + state['Y']

def absy(state, data1, data2):
    address = data2*0x0100 + data1
    return state['Memory'][address + state['Y']]

def abs_read(state, data1, data2):
    print(f'{data2*256 + data1:04x} -> {state["Memory"][data2*0x0100 + data1]}')

    return state['Memory'][data2*0x0100 + data1]

def abs_x_read(state, data1, data2):
    x = state['X']
    print(f'{data2*256 + data1:04x} + {x:02x} -> {state["Memory"][data2*0x0100 + data1 + x]}')

    return state['Memory'][data2*0x0100 + data1 + x]


_ = lambda x: x

instructions = {
    0x09: [ORA, imm],
    0x10: [BPL, imm],
    0x20: [JSR, imm2, _],
    0x29: [AND, imm],
    0x2C: [BIT, abs_read, _],
    # 0x41: [EOR, indx],
    0x4C: [JMP, imm2, _],
    0x60: [RTS],
    0x78: [SEI],
    0x85: [STA, imm],
    0x86: [STX, imm],
    0x88: [DEY],
    0x8A: [TXA],
    0x8D: [STA, imm2, _],
    0x91: [STA, indy],
    0x99: [STA, absy, _],
    0x9A: [TXS],
    0xA0: [LDY, imm],
    0xA2: [LDX, imm],
    0xA9: [LDA, imm],
    0xAD: [LDA, abs_read, _],
    0xB0: [BCS, imm],
    0xBD: [LDA, abs_x_read, _],
    0xC0: [CPY, imm],
    0xC8: [INY],
    0xC9: [CMP, imm],
    0xCA: [DEX],
    0xD0: [BNE, imm],
    0xD8: [CLD],
    0xE0: [CPX, imm],
    0xEE: [INC, imm2, _]
}


##  begin

state = {
    'ProgramCounter': 0,
    'Accumulator': 0, 'X': 0, 'Y': 0,
    'StackRegister': 0,
    'StatusRegister': {
        'Negative': 0,
        'Zero': 0,
        'Decimal': 0,
        'Interrupt': 0,
        'Carry': 0,
        'Overflow': 0
    }
}

memory = np.zeros(0x10000, dtype=np.uint8)
memory[0x8000:0x8000+len(program_data)] = program_data

state['Memory'] = memory


##

def reset():
    state['ProgramCounter'] = state['Memory'][0xFFFD]*0x0100 + state['Memory'][0xFFFC]
    state['StackZero'] = 0x0100
    state['StackOffset'] = 0xFD

def increment():
    opcode = state['Memory'][state['ProgramCounter']]
    state['ProgramCounter'] += 1

    return opcode

def vertical_blank(): state['Memory'][0x2002] = 0x80

ops = {}

def visit(index, text):
    count, text = ops.get(index, (0, text))
    ops[index] = (count + 1, text)


vertical_blank()
reset()

indexes = []
def do(n):
    global last

    for _1 in range(n):
        index = state['ProgramCounter']
        opcode = increment()
        indexes.append(index)

        operation = instructions[opcode.item()]

        if len(operation) == 1:
            op, = operation
            op(state, 0, 0)

            visit(index, f'{opcode:02X} {op.__name__}')

        elif len(operation) == 2:
            op, f1 = operation
            data = increment()

            fy = ",y" if f1 == indy else ""
        
            visit(index, f'{opcode:02X} {op.__name__} .${data:02x}' + fy)
            op(state, f1(state, data), 0)

        elif len(operation) == 3:
            op, f1, f2 = operation
            data1, data2 = increment(), increment()

            if f2 == _:
                fy = ",y" if f1 == absy else ""
                visit(index, f'{opcode:02X} {op.__name__} ${data2:02x}{data1:02x}{fy} ;{data1*0x0100 + data2:04x}')
                op(state, f1(state, data1, data2), 0)

do(12708 + 6611 + 1000)
opcode = state['Memory'][state['ProgramCounter']]

b = {'False': " ", '0': '●', '1': '•', '2': '⋅', '3': '⋅'}
a = lambda i: b[str((i in indexes[-4:]) and indexes[-4:][::-1].index(i))]
ops = sorted(ops.items())
print('\n' + '\n'.join([f'{a(index)}{count:2} {index:02X} {op}' for index, (count, op) in ops]) + '\n')

print()
print(hex(state['ProgramCounter']), state, hex(opcode.item()), opcode.item())
print()

# print(f":{state['Memory'][0x04A0]:X}")
# print(hex(248))