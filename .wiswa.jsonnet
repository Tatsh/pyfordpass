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
  publishing+: { flathub: 'sh.tat.pyfordpass' },
  security_policy_supported_versions: { '0.0.x': ':white_check_mark:' },
  pyproject+: {
    project+: {
      scripts: { ford: 'fordpass.commands:main' },
    },
    tool+: {
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
        },
        include+: [],
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
