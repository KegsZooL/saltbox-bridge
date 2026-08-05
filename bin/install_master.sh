#!/bin/bash

# shellcheck disable=SC2016

# Copyright 2026 Anton Karmanov, Daniil Konarev, Daniil Chistyakov 

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -eu -o pipefail

declare -r timestamp_template="+%Y-%m-%d %H:%M:%S"

declare script_dir
script_dir="$(dirname "${BASH_SOURCE[0]}")"

declare -r bridge_dir="${script_dir}/saltbox-bridge"
declare -r bridge_python_package_dir="${bridge_dir}/saltbox_bridge"

declare -r crt_file_name="redis-ca.crt"
declare -r salt_crt_destination="/etc/salt/ssl/${crt_file_name}"

declare -r correct_head_crt="-----BEGIN CERTIFICATE-----"
declare -r correct_tail_crt="-----END CERTIFICATE-----"

declare -r salt_pin_path=/etc/apt/preferences.d/salt-pin-1001
declare -r salt_keyring_path=/etc/apt/keyrings/salt-archive-keyring.pgp
declare -r salt_apt_sources_path=/etc/apt/sources.list.d/salt.sources
declare -r salt_pip_binary_path="/opt/saltstack/salt/bin/pip3"

declare -r salt_sources_url=https://github.com/saltstack/salt-install-guide/releases/latest/download/salt.sources
declare -r gpg_salt_key_url=https://packages.broadcom.com/artifactory/api/security/keypair/SaltProjectKey/public
declare -r saltbox_bridge_repo_url="https://dev.saltbox.pro/saltbox/saltbox-bridge.git"

declare -r salt_version=3007.13
declare -r salt_pkgs=(
  "salt-common=${salt_version}"
  "salt-master=${salt_version}"
  "salt-minion=${salt_version}"
)
declare -r dependencies=(curl gnupg git rsync netcat-openbsd gettext-base)

declare -ri default_redis_port=6379
declare -r ip_regex='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
declare -r port_regex='^[0-9]+$'

declare -r master_conf_path=/etc/salt/master
declare -r minion_conf_path=/etc/salt/minion
declare -r saltbox_conf_path=/etc/salt/saltbox

declare -r master_conf_tpl="${bridge_dir}/master/templates/master.conf.tpl"
declare -r minion_conf_tpl="${bridge_dir}/master/templates/minion.conf.tpl"
declare -r saltbox_conf_tpl="${bridge_dir}/master/templates/saltbox.conf.tpl"

# shellcheck disable=SC2155
declare -r master_conf_extra_tpl="$(cat <<'EOF'
user: root
salt_box_master_id: %s
EOF
)"

# shellcheck disable=SC2155
declare -r minion_conf_extra_tpl="$(cat <<'EOF'
id: %s
EOF
)"

declare -r saltbox_conf_extra_tpl='redis_host: ${SALTBOX_IP} 
redis_ssl_ca_certs: '"${salt_crt_destination}"'
salt_conf_server: ${SALTBOX_IP}
sshfs_server: ${SALTBOX_IP}'

declare -r master_id_timestamp_format="+%Y%m%d-%H%M%S"

# shellcheck disable=SC2155
declare -r default_master_id="master-$(date "${master_id_timestamp_format}")"

declare -r default_master_log_level="info"
declare -r default_minion_log_level="info"
declare -r default_redis_user="redis"

declare -A messages
declare -r log_pause_seconds=0.5

messages[tittle,en]='
   ####################################################
 ########################################################
##                                                      ##
##      Installing secondary Salt-Master service        ##
##                                                      ##
##                    [Salt.Box]                        ##
##                                                      ##
 #######################################################
   ####################################################
'
messages[tittle,ru]='
   ####################################################
 ########################################################
##                                                      ##
##      Установка стороннего Salt-Master сервиса        ##
##                                                      ##
##                    [Salt.Box]                        ##
##                                                      ##
 #######################################################
   ####################################################
'

messages[root_required,en]='This script must be run as root'
messages[root_required,ru]='Скрипт должен быть запущен от имени root'

messages[unknown_option,en]='Unknown option: %s'
messages[unknown_option,ru]='Неизвестный параметр: %s'

messages[crt_setup,en]='Redis certificate setup:
\t1 - Search for a certificate in the current directory
\t2 - Specify a path to the `redis-ca.crt` file
\tChoice [1/2] (default `1`): '
messages[crt_setup,ru]='Настройка сертификата Redis:
\t1 - Поиск сертификата в текущей директории
\t2 - Указать путь до файла `redis-ca.crt`
\tВыбор [1/2] (по умолчанию `1`): '

messages[crt_not_found,en]='Certificate `redis-ca.crt` not found!'
messages[crt_not_found,ru]='Сертификат `redis-ca.crt` не найден!'

messages[crt_found_success,en]='Certificate `redis-ca.crt` found successfully!'
messages[crt_found_success,ru]='Сертификат `redis-ca.crt` успешно найден!'

messages[crt_specify,en]='Specify the path to the `redis-ca.crt` file: '
messages[crt_specify,ru]='Укажите путь до файла `redis-ca.crt`: '

messages[crt_incorrect_body,en]='Incorrect certificate format!'
messages[crt_incorrect_body,ru]='Неверный формат сертификата!'

messages[crt_install_start,en]='Installing Redis certificate...'
messages[crt_install_start,ru]='Установка сертификата Redis...'

messages[crt_install_success,en]='Redis certificate installed successfully'
messages[crt_install_success,ru]='Сертификат Redis успешно установлен'

messages[crt_install_failed,en]='Failed to install Redis certificate!'
messages[crt_install_failed,ru]='Не удалось установить сертификат Redis!'

messages[help,en]='Install and connect a secondary Salt-Master to SaltBox.
Usage: ./saltbox-master-install.sh [--en_locale|--ru_locale] [-h|--help]
  --en_locale\t\tRun in English
  --ru_locale\t\tRun in Russian (default)
  -h|--help\t\tPrint this message\n
[NOTE] The script must be run as root.
It installs Salt, configures the saltbox-bridge, sets up master/minion
configs, and connects this Salt-Master to SaltBox via Redis.\n
You will be asked to provide the `redis-ca.crt` certificate: search
automatically in the current directory or specify a path.
'
messages[help,ru]='Установка и подключение стороннего Salt-Master к SaltBox.
Использование: ./saltbox-master-install.sh [--en_locale|--ru_locale] [-h|--help]
  --en_locale\t\tЗапустить на английском
  --ru_locale\t\tЗапустить на русском (по умолчанию)
  -h|--help\t\tВывести это сообщение\n
[ПРИМЕЧАНИЕ] Скрипт должен быть запущен от имени root.\n
Скрипт устанавливает Salt, настраивает saltbox-bridge, конфигурирует
master/minion и подключает данный Salt-Master к SaltBox через Redis.\n
Будет предложено указать сертификат `redis-ca.crt`: автопоиск в текущей
директории либо указание пути к файлу.
'

messages[install_salt_deps,en]='Installing Salt dependencies...'
messages[install_salt_deps,ru]='Установка зависимостей Salt...'

messages[install_pkgs,en]='Installing packages: %s'
messages[install_pkgs,ru]='Установка пакетов: %s'

messages[install_pkgs_success,en]='Packages installed successfully'
messages[install_pkgs_success,ru]='Пакеты успешно установлены'

messages[install_pkgs_failed,en]='Failed to install packages!'
messages[install_pkgs_failed,ru]='Не удалось установить пакеты!'

messages[install_salt,en]="Installing Salt v${salt_version}..."
messages[install_salt,ru]="Установка Salt v${salt_version}..."

messages[salt_key_installing,en]='Installing Salt GPG key...'
messages[salt_key_installing,ru]='Установка GPG-ключа Salt...'

messages[salt_key_install_success,en]='Salt GPG key installed successfully'
messages[salt_key_install_success,ru]='GPG-ключ Salt успешно установлен'

messages[salt_key_install_failed,en]='Failed to install Salt GPG key!'
messages[salt_key_install_failed,ru]='Не удалось установить GPG-ключ Salt!'

messages[salt_apt_sources_installing,en]='Installing Salt APT sources...'
messages[salt_apt_sources_installing,ru]='Установка списка источников APT для Salt...'

messages[salt_apt_sources_install_success,en]='Salt APT sources installed successfully'
messages[salt_apt_sources_install_success,ru]='Список источников APT для Salt успешно установлен'

messages[salt_apt_sources_install_failed,en]='Failed to install Salt APT sources!'
messages[salt_apt_sources_install_failed,ru]='Не удалось установить список источников APT для Salt!'

messages[salt_pin_installing,en]='Pinning Salt package version...'
messages[salt_pin_installing,ru]='Закрепление версии пакетов Salt...'

messages[salt_pin_install_success,en]='Salt package version pinned successfully'
messages[salt_pin_install_success,ru]='Версия Salt пакетов успешно закреплена'

messages[salt_pin_install_failed,en]='Failed to pin Salt package version!'
messages[salt_pin_install_failed,ru]='Не удалось закрепить версию Salt пакетов!'

messages[install_salt_success,en]="Salt v${salt_version} installed successfully"
messages[install_salt_success,ru]="Salt v${salt_version} успешно установлен"

messages[specify_saltbox_ip,en]='Specify Saltbox IP address: '
messages[specify_saltbox_ip,ru]='Укажите IP-адрес SaltBox: '

messages[specify_saltbox_port,en]='Specify Redis port (default 6379): '
messages[specify_saltbox_port,ru]='Укажите Redis порт (по умолчанию 6379): '

messages[empty_value,en]='Value cannot be empty!'
messages[empty_value,ru]='Значение не может быть пустым!'

messages[invalid_ip_format,en]='Invalid IP address format!'
messages[invalid_ip_format,ru]='Неверный формат IP-адреса!'

messages[invalid_port_format,en]='Invalid port format!'
messages[invalid_port_format,ru]='Неверный формат порта!'

messages[check_redis_connection,en]='Checking Redis connection...'
messages[check_redis_connection,ru]='Проверка подключения к Redis...'

messages[check_redis_connection_success,en]='Redis connection successful'
messages[check_redis_connection_success,ru]='Подключение к Redis выполнено успешно'

messages[check_redis_connection_failed,en]='Failed to connect to Redis!'
messages[check_redis_connection_failed,ru]='Не удалось подключиться к Redis!'

messages[prepare_salt_dir,en]='Preparing Salt directories...'
messages[prepare_salt_dir,ru]='Подготовка Salt директорий...'

messages[prepare_salt_dir_success,en]='Salt directories prepared successfully'
messages[prepare_salt_dir_success,ru]='Директории Salt успешно подготовлены'

messages[prepare_salt_dir_failed,en]='Failed to prepare Salt directories!'
messages[prepare_salt_dir_failed,ru]='Не удалось подготовить Salt директории!'

messages[saltbox_bridge_cloning,en]='Cloning saltbox-bridge repository...'
messages[saltbox_bridge_cloning,ru]='Клонирование репозитория saltbox-bridge...'

messages[saltbox_bridge_clone_success,en]='saltbox-bridge cloned successfully'
messages[saltbox_bridge_clone_success,ru]='Репозиторий saltbox-bridge успешно клонирован'

messages[saltbox_bridge_clone_failed,en]='Failed to clone saltbox-bridge repository!'
messages[saltbox_bridge_clone_failed,ru]='Не удалось клонировать репозиторий saltbox-bridge!'

messages[saltbox_bridge_updating,en]='Updating saltbox-bridge repository...'
messages[saltbox_bridge_updating,ru]='Обновление репозитория saltbox-bridge...'

messages[saltbox_bridge_update_failed,en]='Failed to update saltbox-bridge repository'
messages[saltbox_bridge_update_failed,ru]='Не удалось обновить репозиторий saltbox-bridge'

messages[saltbox_bridge_dev_switch_failed,en]='Failed to switch to dev branch'
messages[saltbox_bridge_dev_switch_failed,ru]='Не удалось переключиться на ветку dev'

messages[prepare_salt_bridge,en]="Preparing SaltBox Bridge service..."
messages[prepare_salt_bridge,ru]="Настройка SaltBox Bridge сервиса..."

messages[use_local_bridge,en]='Use local saltbox-bridge repository? (y/n, default y): '
messages[use_local_bridge,ru]='Использовать локальный saltbox-bridge репозиторий? (y/n, по умолчанию y): '

messages[use_dev_branch,en]='Use dev branch? (y/n, default n): '
messages[use_dev_branch,ru]='Использовать ветку dev? (y/n, по умолчанию n): '

messages[bridge_has_uncommitted_changes,en]='The local saltbox-bridge has uncommitted changes!'
messages[bridge_has_uncommitted_changes,ru]='В локальном saltbox-bridge есть незакоммиченные изменения!'

messages[confirm_delete_bridge,en]='Confirm: delete and re-clone saltbox-bridge? (y/n, default n): '
messages[confirm_delete_bridge,ru]='Подтвердите: удалить и заново клонировать saltbox-bridge? (y/n, по умолчанию n): '

messages[bridge_delete_cancelled,en]='Deletion cancelled, using existing local copy'
messages[bridge_delete_cancelled,ru]='Удаление отменено, используется существующая локальная копия'

messages[bridge_remove_failed,en]='Failed to remove local saltbox-bridge directory!'
messages[bridge_remove_failed,ru]='Не удалось удалить локальную директорию saltbox-bridge!'

messages[bridge_will_be_deleted,en]='This will PERMANENTLY DELETE the local saltbox-bridge directory:'
messages[bridge_will_be_deleted,ru]='Локальная директория saltbox-bridge будет БЕЗВОЗВРАТНО УДАЛЕНА'

messages[confirm_delete_uncommitted,en]='Uncommitted changes will be lost. Delete anyway? (y/n, default n): '
messages[confirm_delete_uncommitted,ru]='Незакоммиченные изменения будут потеряны. Удалить несмотря на это? (y/n, по умолчанию n): '

messages[sync_bridge_files_start,en]='Syncing saltbox-bridge files...'
messages[sync_bridge_files_start,ru]='Синхронизация файлов saltbox-bridge...'

messages[sync_bridge_files_success,en]='saltbox-bridge files synced successfully'
messages[sync_bridge_files_success,ru]='Файлы saltbox-bridge успешно синхронизированы'

messages[sync_bridge_files_failed,en]='Failed to sync: %s'
messages[sync_bridge_files_failed,ru]='Не удалось синхронизировать: %s'

messages[install_bridge_start,en]='Installing saltbox-bridge Python package...'
messages[install_bridge_start,ru]='Установка Python-пакета saltbox-bridge...'

messages[install_bridge_success,en]='saltbox-bridge package installed successfully'
messages[install_bridge_success,ru]='Пакет saltbox-bridge успешно установлен'

messages[install_bridge_failed,en]='Failed to install saltbox-bridge package!'
messages[install_bridge_failed,ru]='Не удалось установить пакет saltbox-bridge!'

messages[bridge_dir_not_found,en]='saltbox-bridge directory not found: %s'
messages[bridge_dir_not_found,ru]='Директория saltbox-bridge не найдена: %s'

messages[bridge_not_python_package,en]='saltbox-bridge directory is not a valid Python package:'
messages[bridge_not_python_package,ru]='Директория saltbox-bridge не является корректным Python-пакетом:'

messages[salt_pip_not_found,en]='Salt pip3 binary not found: %s'
messages[salt_pip_not_found,ru]='Бинарник pip3 из Salt не найден: %s'

messages[specify_master_id,en]='Specify Salt master ID (default: %s): '
messages[specify_master_id,ru]='Укажите ID для Salt мастера (по умолчанию: %s): '

messages[specify_master_log_level,en]='Specify Salt master log level (default: %s): '
messages[specify_master_log_level,ru]='Укажите уровень логирования для Salt мастера (по умолчанию: %s): '

messages[specify_minion_log_level,en]='Specify Salt minion log level (default: warning): '
messages[specify_minion_log_level,ru]='Укажите уровень логирования для Salt миньона (по умолчанию: %s): '

messages[specify_redis_user,en]='Specify Redis username (default: %s): '
messages[specify_redis_user,ru]='Укажите имя пользователя Redis (по умолчанию: %s): '

messages[specify_redis_password,en]='Specify Redis password: '
messages[specify_redis_password,ru]='Укажите пароль Redis: '

messages[setup_configs_start,en]='Setting up Salt configuration files...'
messages[setup_configs_start,ru]='Настройка конфигурационных файлов Salt...'

messages[master_conf_setup_start,en]='Writing master config...'
messages[master_conf_setup_start,ru]='Запись конфигурации мастера...'

messages[master_conf_setup_success,en]='Master config written successfully'
messages[master_conf_setup_success,ru]='Конфигурация мастера успешно записана'

messages[minion_conf_setup_start,en]='Writing minion config...'
messages[minion_conf_setup_start,ru]='Запись конфигурации миньона...'

messages[minion_conf_setup_success,en]='Minion config written successfully'
messages[minion_conf_setup_success,ru]='Конфигурация миньона успешно записана'

messages[saltbox_conf_setup_start,en]='Writing SaltBox config...'
messages[saltbox_conf_setup_start,ru]='Запись конфигурации SaltBox...'

messages[saltbox_conf_setup_success,en]='SaltBox config written successfully'
messages[saltbox_conf_setup_success,ru]='Конфигурация SaltBox успешно записана'

messages[config_template_not_found,en]='Config template not found:'
messages[config_template_not_found,ru]='Шаблон конфигурации не найден:'

messages[config_render_failed,en]='Failed to render config template:'
messages[config_render_failed,ru]='Не удалось обработать шаблон конфигурации: %s'

messages[setup_configs_start,en]='Setting up Salt configuration files...'
messages[setup_configs_start,ru]='Настройка конфигурационных файлов Salt...'

messages[setup_configs_success,en]='All Salt configuration files set up successfully'
messages[setup_configs_success,ru]='Все конфигурационные файлы Salt успешно настроены'

messages[config_written_to,en]='Config written to: %s'
messages[config_written_to,ru]='Конфигурация записана в: %s'

messages[master_service_enabling,en]='Enabling salt-master service...'
messages[master_service_enabling,ru]='Включение сервиса salt-master...'
 
messages[master_service_enable_failed,en]='Failed to enable salt-master service!'
messages[master_service_enable_failed,ru]='Не удалось включить сервис salt-master!'
 
messages[master_service_restarting,en]='Restarting salt-master service...'
messages[master_service_restarting,ru]='Перезапуск сервиса salt-master...'
 
messages[master_service_restart_failed,en]='Failed to restart salt-master service!'
messages[master_service_restart_failed,ru]='Не удалось перезапустить сервис salt-master!'
 
messages[master_service_not_active,en]='salt-master service is not active after restart!'
messages[master_service_not_active,ru]='Сервис salt-master не активен после перезапуска!'
 
messages[master_service_started_success,en]='salt-master service started successfully'
messages[master_service_started_success,ru]='Сервис salt-master успешно запущен'
 
messages[minion_service_disabling,en]='Disabling salt-minion service...'
messages[minion_service_disabling,ru]='Отключение сервиса salt-minion...'
 
messages[minion_service_disable_failed,en]='Failed to disable salt-minion service (non-critical)'
messages[minion_service_disable_failed,ru]='Не удалось отключить сервис salt-minion (не критично)'
 
messages[minion_service_disabled_success,en]='salt-minion service disabled successfully'
messages[minion_service_disabled_success,ru]='Сервис salt-minion успешно отключён'

LOCALE="ru"

function display_help_msg() {
  local msg
  msg="$(extract_msg_from_aarr help)"
  printf "%b\n" "${msg}"
  exit 0
}

function extract_msg_from_aarr() {
  local key="${1}"
  local extracted_msg
  extracted_msg="${messages[${key},${LOCALE}]}"

  if [[ -z "${extracted_msg}" ]]; then
    extracted_msg="${messages[$key,en]}"
  fi
  printf "%s" "${extracted_msg}"
}

function log() {
  local level="${1}"
  local key="${2}"
  local extra="${3:-}"
  local pause="${4:-${log_pause_seconds}}"

  local timestamp
  timestamp=$(date "${timestamp_template}")

  local template
  template=$(extract_msg_from_aarr "${key}")

  local msg
  if [[ -n "${extra}" ]]; then
    # shellcheck disable=SC2059
    printf -v msg "${template}" "${extra}"
  else
    msg="${template}"
  fi

  local msg_pattern="[%s] [%s] %s\n"
  local output

  # shellcheck disable=SC2059
  printf -v output "${msg_pattern}" "${timestamp}" "${level}" "${msg}"

  if [[ "$level" == "INFO" ]]; then
    printf "%b" "${output}"
  else
    printf "%b" "${output}" >&2
  fi

  if [[ "${pause}" != "0" ]]; then
    sleep "${pause}"
  fi
}

function 00__is_root() {
  if [ "$EUID" -ne 0 ]; then
    log "WARN" root_required
    exit 1
  fi
}

function 01__display_tittle() {
  local tittle_str
  tittle_str="$(extract_msg_from_aarr tittle)"
  printf "%s\n\n" "${tittle_str}"
}


function check_redis_crt() {
  local path="${1}"
  if [[ -f "${path}" ]]; then
    log "INFO" crt_found_success
    
    local head_crt
    head_crt=$(head -n 1 "${path}")

    local tail_crt
    tail_crt=$(tail -n 1 "${path}")

    if [[ "${head_crt}" != "${correct_head_crt}" || \
          "${tail_crt}" != "${correct_tail_crt}" ]]; then
      log "ERROR" crt_incorrect_body
      return 1
    fi
  else
    log "ERROR" crt_not_found
    return 1
  fi
}

function search_redis_crt() {
  local path
  path="${script_dir}/${crt_file_name}"

  if ! check_redis_crt "${path}" 1>&2; then
    return 1
  fi
  printf "%s" "${path}"
}

function get_redis_crt() {
  local path
  local input_msg

  input_msg=$(log "INFO" crt_specify)
  read -rp "${input_msg}" path

  if ! check_redis_crt "${path}" 1>&2; then
    return 1
  fi
  printf "%s" "${path}"
}

function 02__setup_crt() {

  local path_to_crt
  local mode
  choice_msg=$(log "INFO" crt_setup)
  
  while true; do

    read -rp "${choice_msg}" mode
    mode="${mode:-1}"

    case "${mode}" in
      "1"|"Auto search in current dir")
        path_to_crt=$(search_redis_crt)
        if [[ ! -f "${path_to_crt}" ]]; then
          continue
        fi
        break
        ;;
      "2"|"Specify path to certificate")
        path_to_crt=$(get_redis_crt)
        if [[ ! -f "${path_to_crt}" ]]; then
          continue
        fi
        break
        ;;
      *)
        log "WARN" unknown_option "${mode}"
        ;;
    esac
  done
  
  log "INFO" crt_install_start 
  
  local crt_dirname
  crt_dirname=$(dirname "${salt_crt_destination}")

  mkdir_cmd=(mkdir -vp "${crt_dirname}")
  if ! run_indented "${mkdir_cmd[@]}"; then
    log "ERROR" crt_install_failed 
    exit 1
  fi

  cp_cmd=(cp -av "${path_to_crt}" "${salt_crt_destination}")

  if ! run_indented "${cp_cmd[@]}"; then
    log "ERROR" crt_install_failed
    exit 1
  fi
  log "INFO" crt_install_success
}

function indent() {
  sed 's/^/\t│ /'
}

function run_indented() {
  local cmd_display
  cmd_display="$*"

  local border_char="─"
  local width=80

  local top_border
  printf -v top_border '%*s' "${width}" ''
  top_border="${top_border// /${border_char}}"

  printf "\t┌%s\n" "${top_border}"
  printf "\t│ %s\n" "${cmd_display}"
  printf "\t├%s\n" "${top_border}"

  "$@" 2>&1 | indent
  local exit_code="${PIPESTATUS[0]}"

  printf "\t└%s\n" "${top_border}"

  return "${exit_code}"
}

function display_framed() {
  local content="${1}"

  local border_char="─"
  local width=80

  local top_border
  printf -v top_border '%*s' "${width}" ''
  top_border="${top_border// /${border_char}}"

  printf "\t┌%s\n" "${top_border}"
  printf "%s\n" "${content}" | indent
  printf "\t└%s\n" "${top_border}"
}

function apt_install() {

  local pkgs=("${@}")
  local missing_pkgs=()
  local pkgs_str

  pkgs_str=$(printf ", %s" "${pkgs[@]}")
  pkgs_str="${pkgs_str:2}"

  log "INFO" install_pkgs "${pkgs_str}"

  for pkg in "${pkgs[@]}"; do
    if ! dpkg -s "${pkg}" &>/dev/null; then
      missing_pkgs+=("${pkg}")
    fi
  done

  if ! run_indented apt-get update ; then
    log "ERROR" install_pkgs_failed
  fi
  
  local apt_cmd
  apt_cmd=(apt-get install -y --no-install-recommends -V --show-progress "${missing_pkgs[@]}")

  if ! run_indented "${apt_cmd[@]}" ; then
    log "ERROR" install_pkgs_failed
    exit 1
  else
    log "INFO" install_pkgs_success
  fi
}

function 04__install_deps() {
  log "INFO" install_salt_deps
  apt_install "${dependencies[@]}"
}

function pin_salt_version() {
  
  local salt_pin_content
  salt_pin_content="Package: salt-*
  Pin: version ${salt_version}
  Pin-Priority: 1001
  "
  log "INFO" salt_pin_installing 

  if ! cat <<< "${salt_pin_content}" > "${salt_pin_path}"; then
    log "ERROR" salt_pin_install_failed
    exit 1
  fi
  log "INFO" salt_pin_install_success
}

function 05__install_salt() {

  log "INFO" install_salt
  mkdir -p /etc/apt/keyrings
  
  local curl_cmd
  curl_cmd=(curl -fsSL "${gpg_salt_key_url}")

  log "INFO" salt_key_installing
  if ! "${curl_cmd[@]}" | gpg --dearmor > "${salt_keyring_path}"; then
    log "ERROR" salt_key_install_failed
    exit 1
  fi
  log "INFO" salt_key_install_success

  log "INFO" salt_apt_sources_installing 

  if ! curl -fsSL "${salt_sources_url}" > "${salt_apt_sources_path}"; then
    log "ERROR" salt_apt_sources_install_failed
    exit 1
  fi
  log "INFO" salt_apt_sources_install_success

  pin_salt_version
  
  apt_install "${salt_pkgs[@]}"
  log "INFO" install_salt_success
}

function is_valid_port() {
  local port="${1}"
  if [[ ! "${port}" =~ ${port_regex} ]] ||
     (( "${port}" < 1 || "${port}" > 65535 )); then
    return 1
  fi
  return 0
}

function is_valid_ip() {
  local ip="${1}"

  if [[ ! "${ip}" =~ ${ip_regex} ]]; then
    return 1
  fi

  local octet
  for octet in ${ip//./ }; do
    if (( octet > 255 )); then
      return 1
    fi
  done

  return 0
}

function get_endpoint_part() {

  local info_msg_key="${1}"
  local error_msg_key="${2}"
  local validator="${3}"
  local default_value="${4:-}"

  local prompt
  prompt=$(log "INFO" "${info_msg_key}")

  local value="${default_value}"

  while true; do
    read -rp "${prompt}" value
    value="${value:-"${default_value}"}"

    if "${validator}" "${value}"; then
      break
    fi
    
    if [[ -z "${value}" ]]; then
      log "ERROR" empty_value
    else
      log "ERROR" "${error_msg_key}"
    fi
  done

  printf "%s" "${value}"
}


function 03__check_redis_connection() {

  local saltbox_ip
  saltbox_ip="$(get_endpoint_part \
    specify_saltbox_ip \
    invalid_ip_format \
    is_valid_ip)"

  local saltbox_redis_port
  saltbox_redis_port="$(get_endpoint_part \
    specify_saltbox_port \
    invalid_port_format \
    is_valid_port \
    "${default_redis_port}")"

  log "INFO" check_redis_connection

  local netcat_cmd
  netcat_cmd=(nc -vz "${saltbox_ip}" "${saltbox_redis_port}")

  if ! run_indented "${netcat_cmd[@]}"; then
    log "ERROR" check_redis_connection_failed
    exit 1
  fi
  export SALTBOX_IP="${saltbox_ip}"
  log "INFO" check_redis_connection_success
}

function 06__prepare_salt_dir() {

  local dirs=(
    /srv/salt_extmod/{engines,runners,pillar}
    /srv/salt_master_local
    /srv/salt_local
    /srv/salt_custom
    /srv/saltbox_salt
    /srv/sshfs
    /var/lib/saltbox-bridge
    /etc/salt/ssl
  )
  log "INFO" prepare_salt_dir
  
  for dir in "${dirs[@]}"; do
    cmd=(mkdir -pv "${dir}")
    if ! run_indented "${cmd[@]}"; then
      log "ERROR" prepare_salt_dir_failed
      exit 1
    fi
  done
  log "INFO" prepare_salt_dir_success
}

function clone_saltbox_bridge() {
  local target_dir="${1}"

  log "INFO" saltbox_bridge_cloning
  git_clone_cmd=(git clone "${saltbox_bridge_repo_url}" "${target_dir}")

  if ! run_indented "${git_clone_cmd[@]}"; then
    log "ERROR" saltbox_bridge_clone_failed
    exit 1
  fi
  log "INFO" saltbox_bridge_clone_success
}

function update_saltbox_bridge() {
  local dir="${1}"

  if [[ -d "${dir}/.git" ]]; then
    log "INFO" saltbox_bridge_updating
    
    local git_pull_cmd
    git_pull_cmd=(git -C "${dir}" pull)

    if ! run_indented "${git_pull_cmd[@]}"; then
      log "WARN" saltbox_bridge_update_failed
    fi
  fi
}

function switch_dev_branch_if_requested() {

  local dir="${1}"
  local use_dev
  local prompt

  prompt="$(log "INFO" use_dev_branch)"
  read -rp "${prompt}" use_dev

  if [[ "${use_dev}" == "y" ]]; then

    local git_switch_cmd
    git_switch_cmd=(git -C "${dir}" switch dev)

    if ! run_indented "${git_switch_cmd[@]}"; then
      log "WARN" saltbox_bridge_dev_switch_failed
    fi
  fi
}

function bridge_has_uncommitted_changes() {
  local dir="${1}"

  if [[ -d "${dir}/.git" ]]; then
    local unstaged_status
    local staged_status

    if git -C "${dir}" diff --quiet 2>/dev/null; then
      unstaged_status=0
    else
      unstaged_status=1
    fi

    if git -C "${dir}" diff --cached --quiet 2>/dev/null; then
      staged_status=0
    else
      staged_status=1
    fi

    if [[ "${unstaged_status}" == "1" ]] ||
       [[ "${staged_status}" == "1" ]]; then
      return 0
    else
      return 1
    fi
  else
    return 1
  fi
}

function confirm_delete_local_bridge() {
  local dir="${1}"
  local confirm
  local confirm_prompt

  log "WARN" bridge_will_be_deleted

  if bridge_has_uncommitted_changes "${dir}"; then
    log "WARN" bridge_has_uncommitted_changes
    confirm_prompt="$(log "WARN" confirm_delete_uncommitted)"
  else
    confirm_prompt="$(log "WARN" confirm_delete_bridge)"
  fi

  read -rp "${confirm_prompt}" confirm
  confirm="${confirm:-n}"

  if [[ "${confirm}" == "y" ]]; then
    return 0
  else
    return 1
  fi
}

function 07__prepare_saltbox_bridge() {

  log "INFO" prepare_salt_bridge

  if [[ -d "${bridge_dir}" ]]; then
    local use_local
    local prompt

    prompt="$(log "INFO" use_local_bridge)"
    read -rp "${prompt}" use_local
    use_local="${use_local:-y}"

    if [[ "${use_local}" != "y" ]]; then
      if confirm_delete_local_bridge "${bridge_dir}"; then

        local remove_cmd
        remove_cmd=(rm -rvf "${bridge_dir}")

        if ! run_indented "${remove_cmd[@]}"; then
          log "ERROR" bridge_remove_failed
          exit 1
        fi
        clone_saltbox_bridge "${bridge_dir}"
      else
        log "INFO" bridge_delete_cancelled
      fi
    fi
  else
    clone_saltbox_bridge "${bridge_dir}"
  fi
  update_saltbox_bridge "${bridge_dir}"
  switch_dev_branch_if_requested "${bridge_dir}"
}

function 08__sync_bridge_files() {
  
  local -A targets
  targets['engines/']=/srv/salt_extmod/engines/
  targets['runners/']=/srv/salt_extmod/runners/
  targets['pillar/']=/srv/salt_extmod/pillar/
  targets['master/salt_master_local/']=/srv/salt_master_local/
  targets['master/salt_local/']=/srv/salt_local/
  
  log "INFO" sync_bridge_files_start
  
  local source
  for source in "${!targets[@]}"; do

    local destination
    destination="${targets["${source}"]}"
    
    local full_source="${bridge_dir}/"${source}

    local rsync_cmd
    rsync_cmd=(rsync -av --delete "${full_source}" "${destination}")

    if ! run_indented "${rsync_cmd[@]}"; then
      log "ERROR" sync_bridge_files_failed "${source}"
    fi
  done
  log "INFO" sync_bridge_files_success
}

function 09__install_bridge() {

  log "INFO" install_bridge_start
  
  if [[ ! -d "${bridge_python_package_dir}" ]]; then
    log "ERROR" bridge_dir_not_found "${bridge_python_package_dir}"
    exit 1
  fi

  if [[ ! -f "${bridge_python_package_dir}/pyproject.toml" ]]; then
    log "ERROR" bridge_not_python_package "${bridge_python_package_dir}"
    exit 1
  fi

  if [[ ! -x "${salt_pip_binary_path}" ]]; then
    log "ERROR" salt_pip_not_found "${salt_pip_binary_path}"
    exit 1
  fi
  
  local pip_cmd
  pip_cmd=("${salt_pip_binary_path}" install "${bridge_python_package_dir}" --upgrade)

  if ! run_indented "${pip_cmd[@]}"; then
    log "ERROR" install_bridge_failed
    exit 1
  fi
  log "INFO" install_bridge_success
}

function render_config_template() {

  local template_path="${1}"
  local destination_path="${2}"
  local extra_content="${3:-}"

  if [[ ! -f "${template_path}" ]]; then
    log "ERROR" config_template_not_found "${template_path}"
    exit 1
  fi

  local rendered_content
  if ! rendered_content=$(envsubst < "${template_path}"); then
    log "ERROR" config_render_failed "${template_path}"
    exit 1
  fi
  
  local extended_content
  if [[ -n "${extra_content}" ]]; then
    extended_content="${rendered_content}"$'\n'"${extra_content}"
  fi
  printf "%s" "${extended_content}" > "${destination_path}"

  log "INFO" config_written_to "${destination_path}"
  display_framed "${extended_content}"
}

function 10__setup_configs() {
  
  log "INFO" setup_configs_start

  local master_id_prompt
  master_id_prompt="$(log "INFO" specify_master_id "${default_master_id}")"

  local master_id
  read -rp "${master_id_prompt}" master_id
  master_id="${master_id:-${default_master_id}}"

  local master_log_level
  master_log_level_prompt=$(log "INFO" specify_master_log_level "${default_master_log_level}")
  read -rp "${master_log_level_prompt}" master_log_level
  master_log_level="${master_log_level:-${default_master_log_level}}"

  local minion_log_level
  minion_log_level_prompt=$(log "INFO" specify_minion_log_level "${default_minion_log_level}")
  read -rp "${minion_log_level_prompt}" minion_log_level_prompt
  minion_log_level="${minion_log_level:-${default_minion_log_level}}"

  export SALT_MASTER_LOG_LEVEL="${master_log_level}"
  export SALT_MINION_LOG_LEVEL="${minion_log_level}"

  log "INFO" master_conf_setup_start
  
  local master_conf_extra
  # shellcheck disable=SC2059
  printf -v master_conf_extra "${master_conf_extra_tpl}" "${master_id}"
  render_config_template "${master_conf_tpl}" "${master_conf_path}" "${master_conf_extra}"

  log "INFO" minion_conf_setup_start

  local minion_conf_extra
  # shellcheck disable=SC2059
  printf -v minion_conf_extra "${minion_conf_extra_tpl}" "${master_id}"
  render_config_template "${minion_conf_tpl}" "${minion_conf_path}" "${minion_conf_extra}"

  log "INFO" saltbox_conf_setup_start
    
  local redis_user_prompt
  redis_user_prompt="$(log "INFO" specify_redis_user "${default_redis_user}")"

  local redis_user
  read -rp "${redis_user_prompt}" redis_user
  redis_user="${redis_user:-${default_redis_user}}"

  local redis_pwd_prompt
  redis_pwd_prompt="$(log "INFO" specify_redis_password)"

  local redis_pwd
  while true; do
    read -rp "${redis_pwd_prompt}" redis_pwd
    if [[ -n "${redis_pwd}" ]]; then
      break
    fi
    log "WARN" empty_value
  done

  export REDIS_USERNAME="${redis_user}"
  export REDIS_PASSWORD="${redis_pwd}" # TODO: check Redis connection using username and password

  local saltbox_conf_extra
  saltbox_conf_extra=$(envsubst <<< "${saltbox_conf_extra_tpl}")
  render_config_template "${saltbox_conf_tpl}" "${saltbox_conf_path}" "${saltbox_conf_extra}"

  log "INFO" setup_configs_success
}

function 11__enable_master_service() {

  log "INFO" master_service_enabling

  local enable_cmd
  enable_cmd=(systemctl enable salt-master)

  if ! run_indented "${enable_cmd[@]}"; then
    log "ERROR" master_service_enable_failed
    exit 1
  fi

  log "INFO" master_service_restarting

  local restart_cmd
  restart_cmd=(systemctl restart salt-master)

  if ! run_indented "${restart_cmd[@]}"; then
    log "ERROR" master_service_restart_failed
    exit 1
  fi

  if ! systemctl is-active --quiet salt-master; then
    log "ERROR" master_service_not_active
    exit 1
  fi

  log "INFO" master_service_started_success

  log "INFO" minion_service_disabling

  local disable_minion_cmd
  disable_minion_cmd=(systemctl disable --now salt-minion)

  if ! run_indented "${disable_minion_cmd[@]}"; then
    log "WARN" minion_service_disable_failed
  else
    log "INFO" minion_service_disabled_success
  fi
}

function compleate_stages() {
  00__is_root
  01__display_tittle
  02__setup_crt
  03__check_redis_connection
  04__install_deps
  05__install_salt
  06__prepare_salt_dir
  07__prepare_saltbox_bridge
  08__sync_bridge_files
  09__install_bridge
  10__setup_configs
  11__enable_master_service
}

for i in "$@"; do
  case "$i" in
    --en_locale)
      LOCALE="en"
      ;;
    --ru_locale)
      LOCALE="ru"
      ;;
    -h|--help)
      display_help_msg
      ;;
    -*)
      log "WARN" unknown_option "${i}"
      ;;
  esac
done

readonly LOCALE
compleate_stages
