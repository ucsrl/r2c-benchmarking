# About

This repository contains the benchmarking and evaluation infrastructure for [R2C: AOCR-Resilient Diversity with Reactive and Reflective Camouflage](https://ucsrl.de/publications/r2c-eurosys23.pdf), our paper at EuroSys'23.

The benchmarking infrastructure is based on the truly awesome VUsec [instrumentation-infra](https://github.com/vusec/instrumentation-infra) project.
See the [official documentation](https://instrumentation-infra.readthedocs.io/en/master/guides/spec.html) for details on how to use the framework.
We are currently using a fork of the project to support randomized benchmark runs, but plan to upstream the changes as soon as possible.
The fork changes a few internals of the framework to support the `run-random` command (see below) and to improve reporting.
The `run-random` command runs a benchmark a given number of times, but also recompiles the benchmark with a new seed before each iteration.
All the benchmarking configurations are encoded in `setup.py`.

## Tested versions
All the benchmark builds were tested on Debian 10  and `glibc` version `2.28`.

Building the compiler was tested with `clang` version `11.1.0` as C/C++ compiler and CMake version `3.13.4`.
In principle, the build should also work with `gcc` and newer Debian derivatives.
However, building with `gcc` version `8.3.0` led to an error on the system described above.
Consult the LLVM documentation for details on which compiler and glibc version is supported for building LLVM 11.
The R2C implementation is based on the LLVM repository tag `llvmorg-11.1.0-rc3`.

## Dependency installation
### Benchmarking framework
1. Install `fuseiso unzip binutils-dev jq libpcre3-dev libpcre2-dev bison build-essential gettext git pkg-config python ssh`
1. Clone this repository
1. Create a Python virtual environment (e.g. `virtualenv venv`)  and install the packages `PyYaml terminaltables fancytable psutil`

### R2C compiler
To build the modified LLVM compiler, you need a working build toolchain.
On Debian you can install one by issuing `sudo apt-get install build-essential ninja-build`.

### Webkit
You must install the following dependencies for building Webkit: `apt-get install ruby libcairo2 libcairo2-dev libgcrypt20 libgcrypt20-dev libharfbuzz-dev libjpeg-dev libepoxy-dev libsqlite3-dev unifdef libwebp-dev libgles-dev libgtk-3-dev libsoup2.4-dev libxslt1-dev libsecret-1-dev libgirepository1.0-dev libtasn1-6-dev libwpe-1.0-dev libwpebackend-fdo-1.0-dev libgbm-dev libdrm-dev flite1-dev libenchant-2-dev libxt-dev libopenjp2-7-dev libwoff-dev libavif-dev libsystemd-dev libnotify-dev liblcms2-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev gperf libevent-dev libasound2-dev libopus-dev libpulse-dev gtk-doc-tools`
Newer versions of Webkit use Flatpak dependencies for the build, as described at https://trac.webkit.org/wiki/BuildingGtk#Dependencies.
However, newer versions introduce dependencies not available in Debian 10/11 and are also not compatible with the LLVM version that R²C is based on. 


## Building the compiler
You can build the compiler without running any benchmarks by using the command
`venv/bin/python setup.py pkg-build llvm-src-11.0.0`.
The command will download and build all additional build requirements, as well as the modified LLVM compiler.
The command assumes the C compiler `gcc` and the C++ compiler `g++`, but you can override the defaults by setting the environment variable `CC` and `CXX`, respectively.

Note that by default the benchmarking script downloads the newest available version of the compiler.
The artifact evaluation was performed with [![DOI](https://zenodo.org/badge/592759175.svg)](https://zenodo.org/badge/latestdoi/592759175).

The compiler can be found under `build/packages/llvm-src-11.0.0/obj`.

> **WARNING**: Please make sure that environment variables that influence the build (e.g. LDFLAGS) are either empty or contain values compatible with building LLVM.
> This is especially true if you try to (re)build LLVM after building the webservers, since the webserver build commands set environment variables.
> If you accidentally run the pkg-build command with incorrect environment variables, make sure to delete the build/packages/llvm-src-11.0.0/obj and build/packages/llvm-src-11.0.0/install folders afterwards.
> These folders contain the generated CMake configuration and, thus, cache the supplied environment variables.

## Building the compiler manually (optional)
If the automatic download and build of the compiler fails for whatever reason, you can try to build the compiler manually.

1. clone https://github.com/fberlakovich/r2c-llvm.git to `<src-dir>`
1. make sure you have the gold linker installed and set as the system default linker 
1. create a build directory 
1. `cd <build-dir>`
1. build the compiler
    1. For a debug build: `cmake -G Ninja -DLLVM_ENABLE_PROJECTS='clang;compiler-rt' -DLLVM_ENABLE_ASSERTIONS=TRUE -DCMAKE_BUILD_TYPE=Debug -DCMAKE_SHARED_LINKER_FLAGS='-Wl,--gdb-index' -DCMAKE_EXE_LINKER_FLAGS='-Wl,--gdb-index' -DBUILD_SHARED_LIBS=true -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_BINUTILS_INCDIR=/usr/include <src-dir>/llvm`
    2. For a release build: `cmake -G Ninja -DLLVM_ENABLE_PROJECTS="clang;compiler-rt" -DLLVM_ENABLE_ASSERTIONS=TRUE -DBUILD_SHARED_LIBS=true -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_BINUTILS_INCDIR=/usr/include <src-dir>/llvm`
1. ninja -j <number of parallel jobs>

## Running SPEC benchmarks
1. Make sure you have the SPEC CPU 2017 ISO available. For licensing reasons we cannot include the SPEC ISO with the benchmarking code.
1. Create a `config.yaml` file:
    ```
    spec:
      iso: <path to SPEC iso>
    ```

### Evaluating functionality
1. If you just want to test whether R²C compiled benchmarks are function, you can run a single iteration of the benchmarks with full R²C protection:
`venv/bin/python setup.py run-random  spec2017 --parallel proc --parallelmax 1 --iterations 1  -j $(nproc) --benchmarks 600.perlbench_s 602.gcc_s 605.mcf_s 619.lbm_s 620.omnetpp_s 623.xalancbmk_s 625.x264_s 631.deepsjeng_s 638.imagick_s 641.leela_s 644.nab_s 657.xz_s --backup run full-r2c`
1. The results will be located in `results/run.<date>` and can be displayed with e.g.
`venv/bin/python setup.py report spec2017 -f runtime:median:all maxrss:median --aggregate geomean --table fancy  results/run.<date>`

### Evaluating performance
To evaluate R²C's performance, you should run a baseline and a protected configuration and compare the results.
1. To run the full SPEC CPU 2017 suite (incl. floating point) with 10 iterations in the baseline and full R²C configuration, use the following command
`venv/bin/python setup.py run-random  spec2017 --parallel proc --parallelmax 1 --iterations 10  -j $(nproc) --benchmarks 600.perlbench_s 602.gcc_s 605.mcf_s 619.lbm_s 620.omnetpp_s 623.xalancbmk_s 625.x264_s 631.deepsjeng_s 638.imagick_s 641.leela_s 644.nab_s 657.xz_s --backup run baseline full-r2c`
1. The results will be located in `results/run.<date>` and can be displayed with e.g.
`venv/bin/python setup.py report spec2017 -f runtime:median:all maxrss:median --aggregate geomean --table fancy --overhead baseline --show-baseline results/run.<date>`

## Running webserver benchmarks

The throughput benchmarks test which numer of connections fully saturates the CPU.
To calculate the overhead, you need to compare the saturation throughput and latency with a baseline run.
See the [official documentation](https://instrumentation-infra.readthedocs.io/en/master/guides/webservers.html) for more details on the methodology.
If you only want to test whether the instrumented webservers work, running a single configuration (i.e. without baseline) is sufficient.

Depending on the benchmark settings (e.g. number of connections) you might encounter problems with file handle limits.
In particular, the Debian default of 1024 might be too low for a larger number of connections.
In such a case the generated benchmark results for some of the runs are corrupt and cannot be parsed with the `report` command.
You will typically receive an error such as `AssertionError: regex not found in outfile`.
You can check whether file handle limits are a problem by searching for "Too many open file handles" in the result directory, e.g., `grep -R "Too many open files" results/run.X`.
If the search turns up any results, you need to increase the file handle limit for the user running the benchmarks.


### Configuring password-less SSH login
The webserver benchmarks require password-less login via SSH to control either the client or the server side.
The following examples show how to run the webserver benchmarks with the client and server running on the same host.
While this setup is not ideal, it does not require a high-throughput link between client and server.
In the following steps we assume that the commands `ssh infra-client` and `ssh infra-server` both establish an SSH connection with localhost and password-less login.
An example configuration in `.ssh/ssh_conifg` could look as follows
```
Host infra-client
        HostName localhost
        User user
        IdentityFile ~/.ssh/id_localhost

Host infra-client
        HostName localhost
        User user
        IdentityFile ~/.ssh/id_localhost
```

To generate an SSH key specifically for the localhost login, you can use 
```ssh-keygen -t rsa -b 4096 -f $HOME/.ssh/id_localhost```
and add it to your `authorized_keys` file with `cat $HOME/.ssh/id_localhost.pub >> $HOME/.ssh/authorized_keys`.


### Nginx
1. To run a throughput benchmark with a fully protected nginx, where both client and server run on the same machine, use the following commands
```
   THREADS=$(($(nproc) / 2))
   # round the number of processes to the closest power of 2
   MIN_CONNECTIONS=$(venv/bin/python3 -c "import math; print(2**math.ceil(math.log2($THREADS)))")
   venv/bin/python3 setup.py run-random nginx-1.14.2 full-r2c -t bench --parallel=ssh --ssh-nodes infra-client infra-server --remote-client-host localhost --remote-server-host localhost --server-ip localhost --port 20000 --duration 30 --threads $THREADS --iterations 3 --workers $THREADS --worker-connections 1024 --filesize 64 --collect-stats cpu-proc cpu rss --collect-stats-interval 1 --connections $(seq -s ' ' $MIN_CONNECTIONS 16 256) $(seq -s ' ' 384 128 1024) $(seq -s ' ' 1280 256 2048) --restart-server-between-runs
```
1. The results will be located in `results/run.<date>` and can be displayed with e.g.
`venv/bin/python setup.py report nginx-1.14.2 -f cpu:mean throughput:median:stdev_percent 50p_latency:median 75p_latency:median 90p_latency:median 99p_latency:median --aggregate max  --refresh results/run.<date>`

### Apache
1. To run a throughput benchmark with a fully protected Apache, where both client and server run on the same machine, use the following command
```
   THREADS=$(($(nproc) / 2))
   # round the number of processes to the closest power of 2
   MIN_CONNECTIONS=$(venv/bin/python3 -c "import math; print(2**math.ceil(math.log2($THREADS)))")
   venv/bin/python3 setup.py run-random apache-2.4.54 full-r2c -t bench -j $(nproc) --parallel=ssh --ssh-nodes infra-client infra-server --remote-client-host localhost --remote-server-host localhost --server-ip localhost --port 20000 --duration 30  --threads $(($(nproc) / 2)) --iterations 3 --workers $(($(nproc) / 2))  --filesize 64 --collect-stats cpu-proc cpu rss --collect-stats-interval 1 --connections $(seq -s ' ' $MIN_CONNECTIONS 16 256) $(seq -s ' ' 384 128 1024) $(seq -s ' ' 1280 256 2048) --restart-server-between-runs --timeout 5
```
1. The results will be located in `results/run.<date>` and can be displayed with e.g.
`venv/bin/python setup.py report apache-2.4.54 -f cpu:mean throughput:median:stdev_percent 50p_latency:median 75p_latency:median 90p_latency:median 99p_latency:median --aggregate max  --refresh results/run.<date>`

## Building web browsers
> **WARNING**: Building the web browsers requires *a lot* of CPU and memory, especially when using a large number of parallel build jobs. 
> This is especially true because the R²C compiler was not optimized for compilation speed. 
> If you encounter OOM errors, try building with fewer parallel jobs. 
> We have not tested the build on constrained hardware, but only on the TR 3970X machine described in the paper. 

### Building Webkit
Building Webkit is not fully automated yet.
The artifact evaluation was performed with [![DOI](https://zenodo.org/badge/490684741.svg)](https://zenodo.org/badge/latestdoi/490684741).
To build the GTK version with R²C protections enabled, follow these instructions:

1. Fetch the Webkit source from https://github.com/fberlakovich/r2c-webkit, e.g., to `webkit/src`

   The repository contains the version of Webkit we built for the paper (`c9ddaa0e84e3fc69e7f82e8773349b20ad67f2d1`) plus a commit with the required modifications.
   Alternatively, you can clone the official Webkit repository, checkout the mentioned commit and apply the patch in `0001-Disable-btras-for-functions-called-from-non-r2c-code.patch`.
   See the Limitations section in the paper for why the modifications are necessary.
1. Create a build directory, e.g., `webkit/build` and run the following commands (i.e. cmake with certain options set) 
   
   ```shell
   export COMPILER_FLAGS="-flto=thin -O3 -fbtras=10 -fheap-boobytraps=10"
   export LDFLAGS="-flto=thin -Wl,--plugin-opt,-fast-isel=false -fbtras=10 -fheap-boobytraps=10 -Wl,--plugin-opt,-assume-btra-callee=maybe -Wl,--plugin-opt,-prolog-min-padding-instructions=1 -Wl,--plugin-opt,-prolog-max-padding-instructions=5 -Wl,--plugin-opt,-shuffle-functions=true -Wl,--plugin-opt,-shuffle-globals=true -Wl,--plugin-opt,-randomize-reg-alloc=true"
   export LLVM_BUILD_DIR=<llvm-build>
   export WEBKIT_SRC=<webkit-src>
   cmake -DCMAKE_C_COMPILER:FILEPATH="$LLVM_BUILD_DIR/bin/clang" -DCMAKE_RANLIB="$LLVM_BUILD_DIR/bin/llvm-ranlib" -DCMAKE_NM="$LLVM_BUILD_DIR/bin/llvm-nm" -DCMAKE_AR="$LLVM_BUILD_DIR/bin/llvm-ar" -DCMAKE_CXX_COMPILER:FILEPATH="$LLVM_BUILD_DIR/bin/clang++" -DCMAKE_C_FLAGS="$COMPILER_FLAGS" -DCMAKE_CXX_FLAGS="$COMPILER_FLAGS" -DPORT="GTK" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_TYPE=Release -G Ninja -DUSE_WPE_RENDERER=Off -DENABLE_GAMEPAD=OFF -DDEVELOPER_MODE=ON -DENABLE_EXPERIMENTAL_FEATURES=ON "$WEBKIT_SRC"
   ```
      
   Note that the disabled components are not related to R²C, but also had to be disabled for the baseline build.

1. Run `ninja`

Make sure to replace
1. `<llvm-build>` with your LLVM build directory
2. `<webkit-src>` with your Webkit source directory



After building successfully, you will find the binaries below the `bin` directory.
You can run the tests, by running one of the `test*` binaries or start the browser by running `MiniBrowser`.

### Building Chromium
Building Chromium is not fully automated yet.
To build Chromium with R²C protections enabled, follow these instructions:

1. Follow the instructions at https://chromium.googlesource.com/chromium/src/+/main/docs/linux/build_instructions.md to obtain the source code
2. Checkout revision `c77407083a66f4cdaa0811958ae1e1c9c9f6e215` (tag `82.0.4054.2`)
3. Run `gclient sync`
4. On Debian 10 applying the patch `0001-build-fixes.patch` was needed to successfully build, even without R²C protection
5. Apply the patch `0001-disable-r2c-for-function-called-from-JS.patch` in the `v8` directory
5. Create a build directory `mkdir -p <chrome-src>/out/r2c`
6. In the build directory run
   1. Create a file called `args.gn` with the following content
       ```
       enable_nacl=false
       symbol_level=1
       is_debug = false
       is_component_build = false
       clang_use_chrome_plugins = false
       custom_toolchain="//build/toolchain/linux/unbundle:default"
       host_toolchain="//build/toolchain/linux/unbundle:default"
       use_sysroot = false
       use_gnome_keyring = false
       use_unofficial_version_number=false
       enable_vr=false
       enable_nacl=false
       enable_nacl_nonsfi=false
       ```
   2. Run the following command

      `export COMPILER_FLAGS="-flto=thin -O3 -Wno-non-c-typedef-for-linkage -fbtras=10 -fheap-boobytraps=10 -Wno-dtor-typedef -Wno-psabi" && export LDFLAGS="-flto=thin -Wl,--plugin-opt,-fast-isel=false -fbtras=10 -fheap-boobytraps=10 -Wl,--plugin-opt,-assume-btra-callee=maybe -Wl,--plugin-opt,-prolog-min-padding-instructions=1 -Wl,--plugin-opt,-prolog-max-padding-instructions=5 -Wl,--plugin-opt,-shuffle-functions=true -Wl,--plugin-opt,-shuffle-globals=true -Wl,--plugin-opt,-randomize-reg-alloc=true -Wl,--plugin-opt,-x86-max-booby-trap-trampolines=100" && export CC="<llvm-build>/bin/clang" && export CXX="<llvm-build>/bin/clang++" && export NM="<llvm-build>/bin/llvm-nm" && export AR="<llvm-build>/bin/llvm-ar" && export CFLAGS="$COMPILER_FLAGS" && export CXXFLAGS="$COMPILER_FLAGS" && gn args .`

   Note that the disabled warnings are not related to R²C, but also had to be disabled for the baseline build.

7. In the build directory run `ninja`
8. Run chrome with `./chrome --no-sandbox`

Make sure to replace
1. `<llvm-build>` with your LLVM build directory
2. `<chrome-src>` with your Webkit source directory

## Citation

If you find this work useful, please cite our work as follows:

```
@inproceedings{berlakovich2023,
author = {Berlakovich, Felix and Brunthaler, Stefan},
title = {R2C: AOCR-Resilient Diversity with Reactive and Reflective Camouflage},
year = {2023},
booktitle = {Proceedings of the Eighteenth European Conference on Computer Systems},
location = {Rome, Italy},
series = {EuroSys '23}
}
```
