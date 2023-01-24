#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import os
import sys

curdir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(curdir, 'infra'))

from random_experiment import RunRandomCommand
from infra.instances.clang import ParameterizedClang, RandomizingClang

from infra.packages.llvm import LLVMSource

import infra
import yaml

if __name__ == '__main__':

    llvm_path = "https://github.com/fberlakovich/r2c-llvm.git:master"
    llvm_version = "11.0.0"
    c_comp = os.getenv("CC") or "gcc"
    cxx_comp = os.getenv("CXX") or "gcc"
    llvm = LLVMSource(source_type='git', source=llvm_path, version=llvm_version,
                      build_flags=['-DBUILD_SHARED_LIBS=true', '-DLLVM_TARGETS_TO_BUILD=X86',
                                   '-DCMAKE_C_COMPILER=' + c_comp,
                                   '-DCMAKE_CXX_COMPILER=' + cxx_comp,
                                   '-DLLVM_ENABLE_PROJECTS=clang;compiler-rt;lld'])

    def rando_compiler(name):
        return RandomizingClang(llvm, name, optlevel=3, benchmark_env={"HEAP_BOOBYTRAP_SEED": "RNGSEED"})


    setup = infra.Setup(__file__)

    setup.add_command(RunRandomCommand())
    baseline = ParameterizedClang(llvm, "baseline", optlevel=3)
    baseline.add_all_flags(["-flto=thin"])
    baseline.add_linker_flags(["-Wl,--plugin-opt,-fast-isel=false"])
    setup.add_instance(baseline)

    basic_options = ["-Wl,--plugin-opt,-fast-isel=false",
                     "-Wl,--plugin-opt,-rng-seed=RNGSEED"]

    basic_rando = ["-Wl,--plugin-opt,-shuffle-functions=true",
                   "-Wl,--plugin-opt,-shuffle-globals=true",
                   "-Wl,--plugin-opt,-randomize-reg-alloc=true"]

    prolog_rando = ["-Wl,--plugin-opt,-prolog-min-padding-instructions=1",
                    "-Wl,--plugin-opt,-prolog-max-padding-instructions=5"]
    full_layout_rando = basic_options + basic_rando + prolog_rando

    btra_config = ["-Wl,--plugin-opt,-x86-max-booby-trap-trampolines=100",
                   "-Wl,--plugin-opt,-assume-btra-callee=maybe"]

    r2c = rando_compiler("r2c")
    r2c.add_all_flags(["-flto=thin", "-inline-threshold=512", "-fbtras=10", "-fheap-boobytraps=5"])
    r2c.add_all_flags(full_layout_rando + ["-Wl,--plugin-opt,-x86-max-booby-trap-trampolines=100"])
    setup.add_instance(r2c)

    fullr2c = rando_compiler("full-r2c")
    fullr2c.add_all_flags(["-flto=thin", "-fbtras=10", "-fheap-boobytraps=5"])
    fullr2c.add_linker_flags(full_layout_rando + btra_config)
    setup.add_instance(fullr2c)

    for btra_count in [2, 6, 10, 14, 18, 22]:
        r2c_btra = rando_compiler("r2c-btra%s" % btra_count)
        r2c_btra.add_all_flags(["-flto=thin", "-fbtras=%s" % btra_count, "-fheap-boobytraps=5"])
        r2c_btra.add_linker_flags(full_layout_rando + btra_config)
        setup.add_instance(r2c_btra)

    for heap_count in [5, 10, 15, 20]:
        r2c_heap = rando_compiler("r2c-heap%s" % heap_count)
        r2c_heap.add_all_flags(["-flto=thin", "-fbtras=10", "-fheap-boobytraps=%s" % heap_count])
        r2c_heap.add_linker_flags(full_layout_rando + btra_config)
        setup.add_instance(r2c_heap)

    push_only = rando_compiler("r2c-push-only")
    push_only.add_all_flags(["-flto=thin", "-fbtras=10", "-fheap-boobytraps=0"])
    push_only.add_linker_flags(basic_options + btra_config + ["-Wl,--plugin-opt,-use-vex-instructions=false"])
    setup.add_instance(push_only)

    avx_only = rando_compiler("r2c-avx-only")
    avx_only.add_all_flags(["-flto=thin", "-fbtras=10", "-fheap-boobytraps=0"])
    avx_only.add_linker_flags(basic_options + btra_config)
    setup.add_instance(avx_only)

    heap_only = rando_compiler("r2c-heap-only")
    heap_only.add_all_flags(["-flto=thin", "-fbtras=0", "-fheap-boobytraps=5"])
    heap_only.add_linker_flags(basic_options)
    setup.add_instance(heap_only)

    prolog_only = rando_compiler("r2c-prolog-only")
    prolog_only.add_all_flags(["-flto=thin", "-fbtras=0", "-fheap-boobytraps=0"])
    prolog_only.add_linker_flags(basic_options + prolog_rando)
    setup.add_instance(prolog_only)

    basic_rando_instance = rando_compiler("r2c-basic-rando")
    basic_rando_instance.add_all_flags(["-flto=thin", "-fbtras=0", "-fheap-boobytraps=0"])
    basic_rando_instance.add_linker_flags(basic_options + basic_rando)
    setup.add_instance(basic_rando_instance)

    if os.path.isfile('config.yaml'):
        with open('config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        spec_iso = config["spec"]["iso"]


        setup.add_target(infra.targets.SPEC2017(source_type='isofile',
                                                source=spec_iso,
                                                ))
    else:
        print("No SPEC 2017 ISO configured, spec2017 benchmarking target will not be available.")

    setup.add_target(infra.targets.Nginx("1.14.2"))
    setup.add_target(infra.targets.ApacheHttpd("2.4.54", "1.7.0", "1.6.1"))

    setup.main()
