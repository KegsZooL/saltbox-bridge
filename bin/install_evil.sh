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

declare -r salt_optional_path=/opt/saltstack
declare -r salt_python_binary_path="${salt_optional_path}/salt/bin/python3"
declare -r evil_path="${salt_optional_path}/evil-minions"

declare -r repo_evil_url=https://dev.saltbox.pro/saltbox/saltbox-evil-minions.git

declare -r etc_system_path=/etc/systemd/system
declare -r minion_override_conf_path=/etc/salt/minion.d
declare -r evil_env_path=/etc/evil-minions.env

declare -r ip_regex='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
declare -r positive_int_regex='^[1-9][0-9]*$'

# shellcheck disable=SC2155
declare -r evil_env_override_content_tpl="$(cat <<'EOF'
COUNT=%s
LOG_LEVEL=%s
EOF
)"

declare -r evil_override_waiting_content='master_tries: -1
retry_dns: 5
recon_randomize: False
recon_max: 0
'

declare -r evil_log_lvl_map=(
  "1:INFO"
  "2:WARNING"
  "3:ERROR"
  "4:CRITICAL"
  "5:DEBUG"
)

declare -r default_entity_log_lvl="1"
declare -ri default_evil_count=100
declare -r default_evil_master_ip="127.0.0.1"

declare -A messages
declare -r log_pause_seconds=0.5

messages[title,en]='
   ####################################################
 ########################################################
##                                                      ##
##            Installing Salt Evil Minions              ##
##                                                      ##
##                    [Salt.Box]                        ##
##                                                      ##
 #######################################################
   ####################################################
'

messages[title,ru]='
   ####################################################
 ########################################################
##                                                      ##
##          Установка Salt Evil Minions                 ##
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

messages[empty_value,en]='Value cannot be empty!'
messages[empty_value,ru]='Значение не может быть пустым!'

messages[invalid_ip_format,en]='Invalid IP address format!'
messages[invalid_ip_format,ru]='Неверный формат IP-адреса!'

messages[invalid_count_format,en]='Invalid count: must be a positive integer!'
messages[invalid_count_format,ru]='Неверное значение: должно быть положительным целым числом!'

messages[salt_not_found,en]='Salt onedir runtime not found at %s. Install Salt first (e.g. via install_master.sh, or a regular salt-minion/salt-master pkg), then re-run this script.'
messages[salt_not_found,ru]='Не найден onedir-рантайм Salt по пути %s. Сначала установите Salt (например, через install_master.sh, либо обычный пакет salt-minion/salt-master), затем повторите запуск этого скрипта.'

messages[help,en]='Install Salt Evil Minions.

Usage: ./install_evil.sh [--en_locale|--ru_locale] [-h|--help]
  --en_locale\t\tDisplay script text in English
  --ru_locale\t\tDisplay script text in Russian (default)
  -h|--help\t\tPrint this message

[NOTE] The script must be run as root. It requires the Salt onedir runtime
to already be installed on this host (/opt/saltstack/salt/bin/pip3) - it is independent of
saltbox-bridge otherwise and does not install or configure it.

What it does:
\t1. Verifies that the Salt onedir runtime is present
\t2. Asks which master address evil-minions should connect to and how many
\t   evil minions to run
\t3. Clones the saltbox-evil-minions repository
\t4. Installs its systemd units and environment file
\t5. Enables and starts the evil-minions service
'
messages[help,ru]='Установка Salt Evil Minions.

Использование: ./install_evil.sh [--en_locale|--ru_locale] [-h|--help]
  --en_locale\t\tОтображать текст скрипта на английском языке
  --ru_locale\t\tОтображать текст скрипта на русском языке (по умолчанию)
  -h|--help\t\tВывести это сообщение

[ПРИМЕЧАНИЕ] Скрипт должен быть запущен от имени root. Необходимо, чтобы на
хосте уже был установлен onedir-рантайм Salt (/opt/saltstack/salt/bin/pip3) — в
остальном он не зависит от saltbox-bridge и не устанавливает/не настраивает его.

Что делает скрипт:
\t1. Проверяет наличие onedir-рантайма Salt
\t2. Спрашивает, к какому адресу мастера подключаться и сколько злых
\t   миньонов запускать
\t3. Клонирует репозиторий saltbox-evil-minions
\t4. Устанавливает его systemd-юниты и env-файл
\t5. Включает и запускает сервис evil-minions
'

messages[evil_master_ip_choice,en]='Which master address should evil-minions connect to?
\t1 - Use the local master on this host (%s)
\t2 - Specify a different master IP address
\tChoice [1/2] (default `1`): '

messages[evil_master_ip_choice,ru]='К какому адресу мастера должны подключаться evil-minions?
\t1 - Использовать локальный мастер на этом хосте (%s)
\t2 - Указать IP-адрес другого мастера
\tВыбор [1/2] (по умолчанию `1`): '

messages[specify_evil_master_ip,en]='Specify the master IP address for evil-minions: '
messages[specify_evil_master_ip,ru]='Укажите IP-адрес мастера для evil-minions: '

messages[specify_evil_count,en]='Specify the number of evil-minions to run (default: %s): '
messages[specify_evil_count,ru]='Укажите количество evil-minions (по умолчанию: %s): '

messages[specify_evil_log_lvl,en]='Specify Evil Minions log level:
\t1 - INFO (default; normal log information)
\t2 - WARNING
\t3 - ERROR
\t4 - CRITICAL
\t5 - DEBUG (useful for debugging Salt code)
\tChoice [1-5] (default `1`): '

messages[specify_evil_log_lvl,ru]='Укажите уровень логирования для Evil Minions:
\t1 - INFO (по умолчанию; обычная лог-информация)
\t2 - WARNING (предупреждения)
\t3 - ERROR (ошибки)
\t4 - CRITICAL (критические ошибки)
\t5 - DEBUG (для отладки кода Salt)
\tВыбор [1-5] (по умолчанию `1`): '

messages[repo_cloning,en]='Cloning %s repository...'
messages[repo_cloning,ru]='Клонирование репозитория %s...'

messages[repo_clone_success,en]='%s cloned successfully'
messages[repo_clone_success,ru]='Репозиторий %s успешно клонирован'

messages[repo_clone_failed,en]='Failed to clone %s repository!'
messages[repo_clone_failed,ru]='Не удалось клонировать репозиторий %s!'

messages[repo_remove_failed,en]='Failed to remove existing directory for %s!'
messages[repo_remove_failed,ru]='Не удалось удалить существующую директорию для %s!'

messages[write_to_file,en]='Writing file: %s'
messages[write_to_file,ru]='Запись файла: %s'

messages[write_to_file_success,en]='File written successfully: %s'
messages[write_to_file_success,ru]='Файл успешно записан: %s'

messages[write_to_file_failed,en]='Failed to write file: %s'
messages[write_to_file_failed,ru]='Не удалось записать файл: %s'

messages[evil_systemd_installing,en]='Installing evil-minions systemd units...'
messages[evil_systemd_installing,ru]='Установка systemd-юнитов evil-minions...'

messages[evil_systemd_install_success,en]='evil-minions systemd units installed successfully'
messages[evil_systemd_install_success,ru]='Systemd-юниты evil-minions успешно установлены'

messages[evil_systemd_install_failed,en]='Failed to install evil-minions systemd units!'
messages[evil_systemd_install_failed,ru]='Не удалось установить systemd-юниты evil-minions!'

messages[evil_env_install_failed,en]='Failed to install evil-minions environment file!'
messages[evil_env_install_failed,ru]='Не удалось установить env-файл evil-minions!'

messages[install_evil_success,en]='evil-minions installed successfully'
messages[install_evil_success,ru]='evil-minions успешно установлен'

messages[system_service_enabling,en]='Enabling %s service...'
messages[system_service_enabling,ru]='Включение сервиса %s...'

messages[system_service_enable_failed,en]='Failed to enable %s service!'
messages[system_service_enable_failed,ru]='Не удалось включить сервис %s!'

messages[system_service_restarting,en]='Restarting %s service...'
messages[system_service_restarting,ru]='Перезапуск сервиса %s...'

messages[system_service_restart_failed,en]='Failed to restart %s service!'
messages[system_service_restart_failed,ru]='Не удалось перезапустить сервис %s!'

messages[system_service_not_active,en]='%s service is not active after restart!'
messages[system_service_not_active,ru]='Сервис %s не активен после перезапуска!'

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

function 01__display_title() {
  local title_str
  title_str="$(extract_msg_from_aarr title)"
  printf "%s\n\n" "${title_str}"
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

function write_to_file() {

  local content="${1}"
  local file_path="${2}"

  local dir_path
  dir_path="$(dirname "${file_path}")"

  if ! mkdir -p "${dir_path}"; then
    log "ERROR" write_to_file_failed "${file_path}"
    exit 1
  fi

  log "INFO" write_to_file "${file_path}"
  display_framed "${content}"

  if ! printf "%s\n" "${content}" > "${file_path}"; then
    log "ERROR" write_to_file_failed "${file_path}"
    exit 1
  fi
  log "INFO" write_to_file_success "${file_path}"
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

function is_valid_count() {
  local count="${1}"
  if [[ ! "${count}" =~ ${positive_int_regex} ]]; then
    return 1
  fi
  return 0
}

function get_validated_input() {

  local info_msg_key="${1}"
  local error_msg_key="${2}"
  local validator="${3}"
  local default_value="${4:-}"

  local prompt
  prompt=$(log "INFO" "${info_msg_key}" "${default_value}")

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

function clone_repository() {

  local source_url="${1}"
  local destination="${2}"
  local repo_name="${3}"

  if [[ -d "${destination}" ]]; then
    local remove_cmd
    remove_cmd=(rm -rvf "${destination}")

    if ! run_indented "${remove_cmd[@]}"; then
      log "ERROR" repo_remove_failed "${repo_name}"
      exit 1
    fi
  fi

  log "INFO" repo_cloning "${repo_name}"

  local git_clone_cmd
  git_clone_cmd=(git clone "${source_url}" "${destination}")

  if ! run_indented "${git_clone_cmd[@]}"; then
    log "ERROR" repo_clone_failed "${repo_name}"
    exit 1
  fi
  log "INFO" repo_clone_success "${repo_name}"
}

function specify_log_lvl() {

  local prompt_key="${1}"
  local default_choice="${2}"
  shift 2
  local -a level_map=("${@}")

  local prompt
  prompt=$(log "INFO" "${prompt_key}")

  local choice
  local pair
  local key
  local val

  while true; do
    read -rp "${prompt}" choice
    choice="${choice:-${default_choice}}"

    for pair in "${level_map[@]}"; do
      key="${pair%%:*}"
      val="${pair#*:}"
      if [[ "${choice}" == "${key}" ]]; then
        printf "%s" "${val}"
        return 0
      fi
    done
    log "ERROR" unknown_option "${choice}"
  done
}

function enable_system_service() {
  local service_name="${1}"

  log "INFO" system_service_enabling "${service_name}"

  local enable_cmd
  enable_cmd=(systemctl enable "${service_name}")

  if ! run_indented "${enable_cmd[@]}"; then
    log "ERROR" system_service_enable_failed "${service_name}"
    exit 1
  fi

  log "INFO" system_service_restarting "${service_name}"

  local restart_cmd
  restart_cmd=(systemctl restart "${service_name}")

  if ! run_indented "${restart_cmd[@]}"; then
    log "ERROR" system_service_restart_failed "${service_name}"
    exit 1
  fi

  local is_active_cmd
  is_active_cmd=(systemctl is-active --quiet "${service_name}")

  if ! run_indented "${is_active_cmd[@]}"; then
    log "ERROR" system_service_not_active "${service_name}"
    exit 1
  fi
}

function 02__check_salt_prerequisite() {
  if [[ ! -x "${salt_python_binary_path}" ]]; then
    log "ERROR" salt_not_found "${salt_python_binary_path}"
    exit 1
  fi
}

function specify_evil_master_ip() {

  local choice_msg
  choice_msg="$(log "INFO" evil_master_ip_choice "${default_evil_master_ip}")"

  local mode
  while true; do

    read -rp "${choice_msg}" mode
    mode="${mode:-1}"

    case "${mode}" in
      "1")
        printf "%s" "${default_evil_master_ip}"
        return 0
        ;;
      "2")
        get_validated_input \
          specify_evil_master_ip \
          invalid_ip_format \
          is_valid_ip
        return 0
        ;;
      *)
        log "WARN" unknown_option "${mode}"
        ;;
    esac
  done
}

function 03__install_evil() {

  local evil_master_ip
  evil_master_ip="$(specify_evil_master_ip)"

  local evil_count
  evil_count="$(get_validated_input \
    specify_evil_count \
    invalid_count_format \
    is_valid_count \
    "${default_evil_count}")"

  local minion_override_master_conf_path
  minion_override_master_conf_path="${minion_override_conf_path}/master.conf"

  local override_content
  override_content="master: ${evil_master_ip}"

  write_to_file "${override_content}" "${minion_override_master_conf_path}"

  local minion_override_waiting_conf_path
  minion_override_waiting_conf_path="${minion_override_conf_path}/waiting.conf"

  write_to_file "${evil_override_waiting_content}" "${minion_override_waiting_conf_path}"

  local repo_name="Salt Evil Minions"
  clone_repository "${repo_evil_url}" "${evil_path}" "${repo_name}"

  local evil_systemd_dir="${evil_path}/systemd"

  log "INFO" evil_systemd_installing

  local -a evil_systemd_files=(
    "${evil_systemd_dir}/evil-minions.service"
    "${evil_systemd_dir}/evil-minions-restart.service"
    "${evil_systemd_dir}/evil-minions-restart.timer"
  )

  local systemd_cp_cmd
  systemd_cp_cmd=(cp -av "${evil_systemd_files[@]}" "${etc_system_path}/")

  if ! run_indented "${systemd_cp_cmd[@]}"; then
    log "ERROR" evil_systemd_install_failed
    exit 1
  fi

  local evil_env_cp_cmd
  evil_env_cp_cmd=(cp -av "${evil_systemd_dir}/evil-minions.env" "/etc/")

  if ! run_indented "${evil_env_cp_cmd[@]}"; then
    log "ERROR" evil_env_install_failed
    exit 1
  fi
  log "INFO" evil_systemd_install_success

  local evil_log_lvl
  evil_log_lvl=$(specify_log_lvl \
    specify_evil_log_lvl \
    "${default_entity_log_lvl}" \
    "${evil_log_lvl_map[@]}")

  local evil_env_override_content
  # shellcheck disable=SC2059
  printf -v evil_env_override_content \
    "${evil_env_override_content_tpl}" \
    "${evil_count}" \
    "${evil_log_lvl}"

  write_to_file "${evil_env_override_content}" "${evil_env_path}"

  enable_system_service "evil-minions"
  enable_system_service "evil-minions-restart.timer"

  log "INFO" install_evil_success
}

function compleate_stages() {
  00__is_root
  01__display_title
  02__check_salt_prerequisite
  03__install_evil
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
