local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  project_name: 'pyfordpass',
  description: 'FordPass client and CLI.',
  keywords: ['command line', 'ford', 'fordpass'],
  primary_module: 'fordpass',
  version: '0.0.1',
  want_main: true,
  want_flatpak: true,
  local top = self,
  publishing+: { flathub: 'sh.tat.%s' % top.project_name },
  pyproject+: {
    project+: {
      scripts: { [top.primary_module]: '%s.main:main' % top.primary_module },
    },
    tool+: {
      coverage+: {
        report+: {
          omit+: ['fordpass/timezone_map.py', 'fordpass/typing/*.py'],
        },
        run+: {
          omit+: ['fordpass/timezone_map.py', 'fordpass/typing/*.py'],
        },
      },
      pytest+: {
        ini_options+: {
          asyncio_mode: 'auto',
        },
      },
      poetry+: {
        dependencies+: {
          click: utils.latestPypiPackageVersionCaret('click'),
          'curl-cffi': utils.latestPypiPackageVersionCaret('curl-cffi'),
          niquests: utils.latestPypiPackageVersionCaret('niquests'),
          platformdirs: utils.latestPypiPackageVersionCaret('platformdirs'),
          rich: utils.latestPypiPackageVersionCaret('rich'),
          tomlkit: utils.latestPypiPackageVersionCaret('tomlkit'),
        },
        group+: {
          tests+: {
            dependencies+: {
              'pytest-asyncio': utils.latestPypiPackageVersionCaret('pytest-asyncio'),
            },
          },
        },
      },
    },
  },
  docs_conf+: {
    config+: {
      intersphinx_mapping+: {
        bascom: ['https://bascom.readthedocs.io/en/latest/', null],
        click: ['https://click.palletsprojects.com/en/stable/', null],
        curl_cffi: ['https://curl-cffi.readthedocs.io/en/stable/', null],
        niquests: ['https://niquests.readthedocs.io/en/stable/', null],
        platformdirs: ['https://platformdirs.readthedocs.io/en/stable/', null],
        rich: ['https://rich.readthedocs.io/en/stable/', null],
        tomlkit: ['https://tomlkit.readthedocs.io/en/latest/', null],
        typing_extensions: ['https://typing-extensions.readthedocs.io/en/latest/', null],
      },
    },
  },
  flatpak+: { command: top.primary_module },
  snapcraft+: {
    apps+: {
      [top.project_name]+: { command: 'bin/%s' % top.primary_module },
    },
  },
}
