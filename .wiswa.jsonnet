local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  project_name: 'pyfordpass',
  private: true,
  description: 'FordPass client and CLI.',
  keywords: ['command line', 'ford', 'fordpass'],
  primary_module: 'fordpass',
  version: '0.0.0',
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
}
