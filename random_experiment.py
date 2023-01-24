import random

from infra.commands import RunCommand, BuildCommand
from infra.commands.build import default_jobs, load_deps

from infra.util import FatalError


class RunRandomCommand(RunCommand):
    name = 'run-random'
    description = 'run a single target program multiple times with fresh builds in between'

    def add_args(self, parser):
        target_parsers = parser.add_subparsers(
            title='target', metavar='TARGET', dest='target',
            help=' | '.join(self.targets))
        target_parsers.required = True

        for target in self.targets.values():
            tparser = target_parsers.add_parser(target.name)

            tparser.add_argument('instances', nargs='+',
                                 metavar='INSTANCE', choices=self.instances,
                                 help=' | '.join(self.instances))
            tparser.add_argument('--force-rebuild-deps', action='store_true',
                                 help='force rebuilding of dependencies (implies --build)')
            tparser.add_argument('-j', '--jobs', type=int, default=default_jobs,
                                 help='maximum number of build processes (default %d)' %
                                      default_jobs)
            tparser.add_argument('-i', '--iterations', metavar='ITERATIONS',
                                 type=int, default=1,
                                 help='number of runs per benchmark')

            self.add_pool_args(tparser)
            target.add_run_args(tparser)

    def run(self, ctx):
        target = self.targets[ctx.args.target]
        instances = self.instances.select(ctx.args.instances)
        pool = self.make_pool(ctx)

        iterations = ctx.args.iterations
        for instance in instances:
            ctx.log.info('building and running instance %s' % instance.name)
            for iteration in range(0, iterations):
                oldctx = ctx.copy()
                seed = str(random.randint(0, 0xFFFFFF))
                ctx.rngseed = seed
                ctx.uniqueid = seed
                ctx.log.info('starting iteration %d with seed %s' % (iteration + 1, ctx.rngseed))
                ctx.args.dry_run = False

                ctx.args.targets = [ctx.args.target]
                ctx.args.packages = []
                ctx.args.deps_only = False
                ctx.args.clean = False
                ctx.args.relink = False

                # TODO support running each benchmark seed multiple times
                ctx.args.iterations = 1

                ctx.args.instances = [instance.name]

                build_command = BuildCommand()
                build_command.set_maps(self.instances, self.targets, self.packages)

                # TODO support remote building with SSHPool (currently only SPEC supports this)
                if ctx.args.parallel == 'ssh':
                    import copy
                    # decouple from oldctx
                    ctx.args = copy.deepcopy(ctx.args)

                    # create a backup copy for the run command
                    args_before_build = copy.deepcopy(ctx.args)
                    ctx.args.parallel = None
                    ctx.args.ssh_nodes = ''
                    build_command.run(ctx)

                    # restore the args before the build
                    ctx.args = args_before_build
                else:
                    build_command.run(ctx)
                ctx.args = oldctx.args

                load_deps(ctx, target)

                ctx.log.info('running %s-%s' % (target.name, instance.name))

                load_deps(ctx, instance)
                instance.prepare_run(ctx)
                target.goto_rootdir(ctx)

                if not self.call_with_pool(target.run, (ctx, instance), pool):
                    raise FatalError('target %s does not support parallel runs' %
                                     target.name)

                ctx = oldctx

                if pool:
                    pool.wait_all()
