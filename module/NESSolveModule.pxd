
# distutils: language = c++

cdef extern from "NESSolveModule.cu" namespace "NESSolveModule":
    cdef void run(const unsigned char* file_location, int file_location_size,
                  char* actions, int num_instances, int num_actions,
                  int num_blocks,
                  float* data_lines_out, char* hash_sets_out,
                  char* frames_red_out, char* frames_green_out, char* frames_blue_out) except +
