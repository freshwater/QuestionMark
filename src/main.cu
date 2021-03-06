
#include <iostream>
#include <fstream>
#include <iomanip>
#include <vector>
#include <math.h>

#include <chrono>

#define DO_SOFTWARE true
#define MAXFRAMES (60*1 + 30)
#define NUM_INSTRUCTIONS 1000000
#define OBSERVED_INSTANCE 0
#define FRAMEDATA_SIZE 256*240
// #define DEBUG 1

// #define SOFTWARE "Donkey Kong.nes"
// #define SOFTWARE "nestest.nes"
// #define SOFTWARE "01-basics.nes"
// #define SOFTWARE "digdug.nes"
// #define SOFTWARE "Spy vs Spy (USA).nes"
// #define SOFTWARE "Bubble Bobble (U).nes"
#define SOFTWARE "Super Mario Bros..nes"
// #define SOFTWARE "Mario Bros (JU).nes"
// #define SOFTWARE "Spelunker (USA).nes"

typedef uint16_t int16u_t;
typedef uint8_t int8u_t;
typedef uint8_t bit_t;

struct SystemState;
struct ComputationState;

#include "states.h"
#include "regions.h"
#include "_instructions.h"
#include "utilities.h"

__device__
void operationTransition(uint8_t opcode, SystemState* state, ComputationState* computation_state, Memory& memory) {
    instructions[opcode].transition(state, computation_state, memory);
}

/* */

__global__
void add(SystemState* systems, int num_instructions)
{
    int instance_index = blockIdx.x*(blockDim.x) + threadIdx.x;

    ComputationState state;
    state.program_counter = systems[instance_index].program_counter_initial;
    state.stack_offset = systems[instance_index].stack_offset_initial;

    Memory memory;
    for (int i = 0; i < sizeof(Memory); i++) {
        memory.array[i] = systems[instance_index].global_memory.array[i];
    }

    for (int i = 0; i < num_instructions; i++) {
        systems[instance_index].next(&state, memory);
    }
}


/* */

int tests(void)
{
    int num_states = 15;
    int num_trace_lines = 100000;
    SystemState *states;
    Trace *trace_lines;

    uint64_t num_instructions = 0;
    std::cin >> num_instructions;

    std::cout << "NUM_INSTRUCTIONS [ " << num_instructions << ", " << sizeof(SystemState) << " ]\n";

    cudaMallocManaged(&states, num_states*sizeof(SystemState));
    cudaMallocManaged(&trace_lines, num_trace_lines*sizeof(Trace));

    /* */

    std::vector<char> program_data = romFileRead("roms/nestest.nes").first;
    std::vector<std::vector<std::string>> log_lines = logRead("data/nestest.log");

    for (int i = 0; i < num_states; i++) {
        states[i] = SystemState(program_data, 0xC000 + i - OBSERVED_INSTANCE, 0xC000);
        states[i].trace_lines = trace_lines;
    }

    /* */

    auto start = std::chrono::high_resolution_clock::now();

    add<<<1, num_states>>>(states, num_instructions);
    cudaDeviceSynchronize();

    auto stop = std::chrono::high_resolution_clock::now();
    std::cout << "\n> " << std::chrono::duration_cast<std::chrono::microseconds>(stop - start).count() << "\n\n";

    /* */

    #ifdef DEBUG

    std::cout << "\n";
    for (int i = 0; i < num_states; i++) {
        if (i == OBSERVED_INSTANCE || i == OBSERVED_INSTANCE + 1) {
            std::cout << "--------------------------" << "\n";
        }

        std::cout << traceLineFormat(states[i].traceLineLast) << "\n";
    }

    std::cout << "\n";

    /* */

    int mismatch_count = 0;
    for (int i = 0; i < states[OBSERVED_INSTANCE].trace_lines_index; i++) {
        std::string reference = logLineFormat(log_lines[i]);
        std::string actual = traceLineFormat(trace_lines[i], false);

        if (reference == actual) {
            std::cout << std::hex << std::setw(2) << std::setfill('0') << std::uppercase << i << " ";
            std::cout << "│ " << actual << "\n";
        } else {
            std::cout << "\n" << std::hex << std::setw(2) << std::setfill('0') << std::uppercase << i << "";
            std::cout << " · " << reference << "\n";
            std::cout << "     " << lineCompare(reference, actual) << "\n";

            mismatch_count++;
        }
    }

    std::cout << "\n" << mismatch_count << "\n" << std::endl;

    #endif

    /* */

    cudaFree(states);
    cudaFree(trace_lines);

    return 0;
}

int software(void)
{
    int num_states = 15;
    int num_trace_lines = 1000000;
    SystemState *states;
    Trace *trace_lines;
    uint8_t* frames_red;
    uint8_t* frames_green;
    uint8_t* frames_blue;

    std::cout << "\n[]\n\n" << std::endl;

    cudaMallocManaged(&states, num_states*sizeof(SystemState));
    cudaMallocManaged(&trace_lines, num_trace_lines*sizeof(Trace));
    cudaMallocManaged(&frames_red, FRAMEDATA_SIZE);
    cudaMallocManaged(&frames_green, FRAMEDATA_SIZE);
    cudaMallocManaged(&frames_blue, FRAMEDATA_SIZE);

    /* */

    std::string software = SOFTWARE;

    auto program_data = romFileRead("roms/" + software).first;
    auto character_data = romFileRead("roms/" + software).second;

    std::vector<std::vector<std::string>> log_lines = logRead("data/nestest.log");

    for (int i = 0; i < num_states; i++) {
        states[i] = SystemState(program_data, character_data);
    }

    states[OBSERVED_INSTANCE].trace_lines = trace_lines;
    states[OBSERVED_INSTANCE].frames_red = frames_red;
    states[OBSERVED_INSTANCE].frames_green = frames_green;
    states[OBSERVED_INSTANCE].frames_blue = frames_blue;

    memset(frames_red, 111, FRAMEDATA_SIZE);

    /* */

    auto start = std::chrono::high_resolution_clock::now();

    add<<<1, num_states>>>(states, NUM_INSTRUCTIONS);
    cudaDeviceSynchronize();

    auto stop = std::chrono::high_resolution_clock::now();
    std::cout << "\n> " << std::chrono::duration_cast<std::chrono::microseconds>(stop - start).count() << "\n\n";

    // std::vector<char> data1(std::begin(states[OBSERVED_INSTANCE].memory.ppu_memory), std::end(states[OBSERVED_INSTANCE].memory.ppu_memory));
    // std::vector<char> data2(std::begin(states[OBSERVED_INSTANCE].memory.ppu_OAM_memory), std::end(states[OBSERVED_INSTANCE].memory.ppu_OAM_memory));

    // std::vector<char> data3(FRAMEDATA_SIZE);
    // std::vector<char> data4(FRAMEDATA_SIZE);
    // std::vector<char> data5(FRAMEDATA_SIZE);
    // memcpy(data3.data(), frames_red, FRAMEDATA_SIZE);
    // memcpy(data4.data(), frames_green, FRAMEDATA_SIZE);
    // memcpy(data5.data(), frames_blue, FRAMEDATA_SIZE);

    // imageWrite(data1, data2, data3, data4, data5);

    /* */

    #ifdef DEBUG

    std::cout << states[OBSERVED_INSTANCE].trace_lines_index << "\n";

    for (int i = 0; i < states[OBSERVED_INSTANCE].trace_lines_index; i++) {
        std::cout << std::hex << std::setw(2) << std::setfill('0') << std::uppercase << i << " ";
        std::cout << "│ " << traceLineFormat(trace_lines[i], true) << "\n";
    }

    std::cout << std::endl;

    #endif

    /* */

    cudaFree(states);
    cudaFree(trace_lines);
    cudaFree(frames_red);
    cudaFree(frames_green);
    cudaFree(frames_blue);

    return 0;
}

int main(void)
{
    if (DO_SOFTWARE) {
        return software();
    } else {
        return tests();
    }
}