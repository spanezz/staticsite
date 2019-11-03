from .core import Settings
from .site import Site
from .utils import timings
import sys
import os
import logging

log = logging.getLogger()


class CmdlineError(RuntimeError):
    pass


class SiteCommand:
    # Command name (as used in command line)
    # Defaults to the lowercased class name
    NAME = None

    # Command description (as used in command line help)
    # Defaults to the strip()ped class docstring.
    DESC = None

    def __init__(self, args):
        self.args = args

        self.setup_logging(args)

        settings_files = ['settings.py', '.staticsite.py']

        # Default to current directory if project was not provided.
        # If the project was provided and is a .py file, load it as settings.
        if args.project:
            if os.path.isfile(args.project) and args.project.endswith(".py"):
                settings_file = os.path.abspath(args.project)
                self.root, settings_file = os.path.split(settings_file)
                settings_files.insert(0, settings_file)
            else:
                self.root = os.path.abspath(args.project)
        else:
            self.root = os.getcwd()

        self.settings = Settings()

        # "Repo mode", adjust paths if README.md exists in the root
        if os.path.isfile(os.path.join(self.root, 'README.md')):
                self.settings.CONTENT = self.root
                self.settings.OUTPUT = self.root + '.site.out'

        # Load settings (optional)
        settings_files = (os.path.join(self.root, f) for f in settings_files)
        settings_file = next(filter(os.path.isfile, settings_files), None)
        if settings_file:
            self.settings.load(settings_file)

        # Command line overrides for settings
        if self.args.theme:
            self.settings.THEME = (os.path.abspath(self.args.theme),)
        if self.args.content:
            self.settings.CONTENT = os.path.abspath(self.args.content)
        if self.args.archetypes:
            self.settings.ARCHETYPES = os.path.abspath(self.args.archetypes)
        if self.args.output:
            self.settings.OUTPUT = os.path.abspath(self.args.output)

        # Double check that root points to something that looks like a project
        self.content_root = os.path.join(self.root, self.settings.CONTENT)
        if not os.path.exists(self.content_root):
            raise CmdlineError("Content directory {} does not exist".format(self.content_root))

        # Pick the first valid theme directory
        self.theme_root = None
        candidate_themes = self.settings.THEME
        if isinstance(candidate_themes, str):
            candidate_themes = (candidate_themes,)
        for themedir in candidate_themes:
            themedir = os.path.join(self.root, themedir)
            if os.path.isdir(themedir):
                self.theme_root = themedir
                break
        if self.theme_root is None:
            raise CmdlineError(
                    "None of the configured theme directories ({}) seem to exist".format(
                        ", ".join(self.settings.THEME)))

    def setup_logging(self, args):
        FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
        if args.debug:
            logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format=FORMAT)
        elif args.verbose:
            logging.basicConfig(level=logging.INFO, stream=sys.stderr, format=FORMAT)
        else:
            logging.basicConfig(level=logging.WARN, stream=sys.stderr, format=FORMAT)

    def load_site(self):
        # Instantiate site
        site = Site(settings=self.settings)
        site.draft = self.args.draft

        # Read and analyze site contents
        with timings("Read site in %fs"):
            site.load_theme(self.theme_root)
            site.load_content(self.content_root)

        with timings("Analysed site tree in %fs"):
            site.analyze()

        return site

    @classmethod
    def make_subparser(cls, subparsers):
        name = cls.NAME
        if name is None:
            name = cls.__name__.lower()

        desc = cls.DESC
        if desc is None:
            desc = cls.__doc__.strip()

        parser = subparsers.add_parser(name, help=desc)
        parser.add_argument("project", nargs="?",
                            help="project directory or .py configuration file (default: the current directory)")
        parser.add_argument("--theme", help="theme directory location. Overrides settings.THEME")
        parser.add_argument("--content", help="content directory location. Overrides settings.CONTENT")
        parser.add_argument("--archetypes", help="archetypes directory location. Override settings.ARCHETYPES")
        parser.add_argument("-o", "--output", help="output directory location. Override settings.OUTPUT")
        parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
        parser.add_argument("--draft", action="store_true", help="do not ignore pages with date in the future")
        parser.add_argument("--debug", action="store_true", help="verbose output")
        parser.set_defaults(handler=cls)

        return parser
