# Renamarr (previously sonarr-series-scanner)

With the addition of radarr support, I've decided to rename this project to Renamarr

## Quick Start

### docker

1) Copy/Rename [config.yml.example](docker/config.yml.example) to `config.yml`
2) Update `config.yml` as needed.
    * See [Configuration](#configuration) for further explanation
3) Bring up app using provided [docker-compose.yml](docker/docker-compose.yml)

### helm

coming soon


## How it works

### Renamarr

This job uses the [Sonarr API](https://sonarr.tv/docs/api/)/[Radarr API](https://radarr.video/docs/api/) to do the following

* Iterate over all items (Movies or Series)
  * Checks if any items need to be renamed
    * Radarr [get_api_v3_rename](https://radarr.video/docs/api/#/RenameMovie/get_api_v3_rename)
    * Sonarr [get_api_v3_rename](https://sonarr.tv/docs/api/#/RenameEpisode/get_api_v3_rename)
  * Triggers a rename on any item that need be renamed
    * Series renames are batched up, for one rename call per series
    * Movie renames are initiated per movie.
      * Example, 1 movie, 2 files. There will be 2 rename API calls

#### Analyze Files
This config option is useful if you have audio/video codec information as part of your mediaformat, and you are transcoding files after import. This will initiate a rescan of the files in your library, so that the mediainfo will be udpated. Then renamarr will come through and detect changes, and rename the files


### Series Scanner (Sonarr Only)
This job uses the [Sonarr API](https://sonarr.tv/docs/api/) to do the following

* Iterate over continuing [series](https://sonarr.tv/docs/api/#/Series/get_api_v3_series)
  * If a series has an episode airing within `config.sonarr[].series_scanner.hours_before_air`
    * default value of 4, max value of 12
  * OR
  * An episode that has aired previously
  * With a title of TBA (excluding specials)
    * will trigger a series refresh, to hopefully pull new info from The TVDB

This should prevent too many API calls to the TVDB, refreshing individual series, hourly

### Usage

The application run immediately on startup, and then continue to schedule jobs every hour (+- 5 minutes) after the first execution.

### Configuration

| Name                                       | Type    | Required | Default Value | Description                                                                                                                                      |
| ------------------------------------------ | ------- | -------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sonarr`                                   | Array   | Yes      | []            | One or more sonarr instances                                                                                                                     |
| `sonarr[].name`                            | string  | Yes      | N/A           | user friendly instance name, used in log messages                                                                                                |
| `sonarr[].url`                             | string  | Yes      | N/A           | url for sonarr instance                                                                                                                          |
| `sonarr[].api_key`                         | string  | Yes      | N/A           | api_key for sonarr instance                                                                                                                      |
| `sonarr[].series_scanner.enabled`          | boolean | No       | False         | enables/disables series_scanner functionality                                                                                                    |
| `sonarr[].series_scanner.hourly_job`       | boolean | No       | False         | disables hourly job. App will exit after first execution                                                                                         |
| `sonarr[].series_scanner.hours_before_air` | integer | No       | 4             | The number of hours before an episode has aired, to trigger a rescan when title is TBA                                                           |
| `sonarr[].renamarr.enabled`                | boolean | No       | False         | enables/disables renamarr functionality                                                                                                          |
| `sonarr[].renamarr.hourly_job`             | boolean | No       | False         | disables hourly job. App will exit after first execution                                                                                         |
| `sonarr[].renamarr.analyze_files`          | boolean | No       | False         | This will initiate a rescan of the files in your library. This is helpful if you are transcoding files, and the audio/video codecs have changed. |
| `radarr[].renamarr.enabled`                | boolean | No       | False         | enables/disables renamarr functionality                                                                                                          |
| `radarr[].renamarr.hourly_job`             | boolean | No       | False         | disables hourly job. App will exit after first execution                                                                                         |
| `radarr[].renamarr.analyze_files`          | boolean | No       | False         | This will initiate a rescan of the files in your library. This is helpful if you are transcoding files, and the audio/video codecs have changed. |

### Environment Variables

Renamarr supports environment variable substitution in the configuration file. This is especially useful for sensitive data like API keys.

#### Syntax

You can use the following syntax in your `config.yml`:

- `${VAR_NAME}` - Substitutes the environment variable `VAR_NAME`. If the variable doesn't exist, the original `${VAR_NAME}` text is kept.
- `${VAR_NAME:-default_value}` - Substitutes the environment variable `VAR_NAME`, or uses `default_value` if the variable doesn't exist.

#### Example

```yaml
sonarr:
  - name: tv
    url: https://sonarr.tld:8989
    api_key: ${SONARR_API_KEY:-fallback-key}
    renamarr:
      enabled: true
      hourly_job: true

radarr:
  - name: movies
    url: https://radarr.tld:7878
    api_key: ${RADARR_API_KEY}
    renamarr:
      enabled: true
      hourly_job: true
```

#### Docker Compose Usage

When using Docker Compose, you can set environment variables in your `.env` file:

```env
SONARR_API_KEY=your-actual-sonarr-api-key
RADARR_API_KEY=your-actual-radarr-api-key
```

And reference them in your `docker-compose.yml`:

```yaml
services:
  renamarr:
    container_name: renamarr
    image: ghcr.io/hollanbm/renamarr:latest
    environment:
      - SONARR_API_KEY=${SONARR_API_KEY}
      - RADARR_API_KEY=${RADARR_API_KEY}
    volumes:
      - ./config.yml:/config/config.yml:ro
```

### Local Setup

#### Requirements

* [Python 3.13](https://www.python.org/downloads/release/python-3130/)
* [pipx](https://pipx.pypa.io/stable/installation/)
* [poetry](https://python-poetry.org/docs/#installation)

#### devcontainer

There is a [devcontainer](https://containers.dev/) provided; it is optional but recommended.
[DevContainer's in VS Code](https://code.visualstudio.com/docs/devcontainers/containers)

####

You will need to create `config.yml` in the root of the repo, to mount your config within the devcontainer

```shell
$ poetry install

$ poetry run python src/main.py
```

#### Unit Tests
```shell
$ pytest
```
