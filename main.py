import requests
import json
import calendar
import datetime
import sys

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found! Please create it based on config.json.template")
        sys.exit(1)
    except json.JSONDecodeError:
        print("config.json contains invalid JSON.")
        sys.exit(1)

def create_attendance_shift(employee_id, date, clock_in, clock_out, cookie):
    url = 'https://api.factorialhr.com/graphql?CreateAttendanceShift=null'
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Pragma": "no-cache",
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-site",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Mode": "cors",
        "Origin": "https://app.factorialhr.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
        "Referer": "https://app.factorialhr.com/",
        "Cookie": cookie,
        "Sec-Fetch-Dest": "empty",
        "Priority": "u=3, i",
        "x-factorial-version": "0b838be1f20fd4e99fe726da2c9fd0a01a8f1258",
        "x-deployment-phase": "default",
        "x-factorial-origin": "web"
    }

    payload = {
        "operationName": "CreateAttendanceShift",
        "variables": {
            "date": date,
            "employeeId": employee_id,
            "clockIn": clock_in,
            "clockOut": clock_out,
            "referenceDate": date,
            "source": "desktop",
            "timeSettingsBreakConfigurationId": 3456,
            "workable": True
        },

        "query": (
            "mutation CreateAttendanceShift($clockIn: ISO8601DateTime, $clockOut: ISO8601DateTime, $date: ISO8601Date!, $employeeId: Int!, $halfDay: String, $locationType: AttendanceShiftLocationTypeEnum, $observations: String, $referenceDate: ISO8601Date!, $source: AttendanceShiftSourceEnum, $timeSettingsBreakConfigurationId: Int, $workable: Boolean) {\n"
            "  attendanceMutations {\n"
            "    createAttendanceShift(\n"
            "      clockIn: $clockIn\n"
            "      clockOut: $clockOut\n"
            "      date: $date\n"
            "      employeeId: $employeeId\n"
            "      halfDay: $halfDay\n"
            "      locationType: $locationType\n"
            "      observations: $observations\n"
            "      referenceDate: $referenceDate\n"
            "      source: $source\n"
            "      timeSettingsBreakConfigurationId: $timeSettingsBreakConfigurationId\n"
            "      workable: $workable\n"
            "    ) {\n"
            "      errors {\n"
            "        ...ErrorDetails\n"
            "        __typename\n"
            "      }\n"
            "      shift {\n"
            "        employee {\n"
            "          id\n"
            "          attendanceBalancesConnection(endOn: $referenceDate, startOn: $referenceDate) {\n"
            "            nodes {\n"
            "              ...TimesheetBalance\n"
            "              __typename\n"
            "            }\n"
            "            __typename\n"
            "          }\n"
            "          attendanceWorkedTimesConnection(endOn: $referenceDate, startOn: $referenceDate) {\n"
            "            nodes {\n"
            "              ...TimesheetWorkedTime\n"
            "              __typename\n"
            "            }\n"
            "            __typename\n"
            "          }\n"
            "          __typename\n"
            "        }\n"
            "        ...TimesheetPageShift\n"
            "        __typename\n"
            "      }\n"
            "      __typename\n"
            "    }\n"
            "    __typename\n"
            "  }\n"
            "}\n"
            "\n"
            "fragment TimesheetBalancePoolBlock on AttendanceTimeBlock {\n"
            "  equivalentMinutesInCents\n"
            "  minutes\n"
            "  name\n"
            "  rawMinutesInCents\n"
            "  timeSettingsCustomTimeRangeCategoryId\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment TimesheetTimeSettingsBreakConfiguration on TimeSettingsBreakConfiguration {\n"
            "  id\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment TimesheetPageWorkplace on LocationsLocation {\n"
            "  id\n"
            "  name\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment ErrorDetails on MutationError {\n"
            "  ... on SimpleError {\n"
            "    message\n"
            "    type\n"
            "    __typename\n"
            "  }\n"
            "  ... on StructuredError {\n"
            "    field\n"
            "    messages\n"
            "    __typename\n"
            "  }\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment TimesheetBalance on AttendanceBalance {\n"
            "  id\n"
            "  balancePools {\n"
            "    transfers {\n"
            "      ...TimesheetBalancePoolBlock\n"
            "      __typename\n"
            "    }\n"
            "    type\n"
            "    usages {\n"
            "      ...TimesheetBalancePoolBlock\n"
            "      __typename\n"
            "    }\n"
            "    __typename\n"
            "  }\n"
            "  dailyBalance\n"
            "  dailyBalanceFromContract\n"
            "  dailyBalanceFromPlanning\n"
            "  date\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment TimesheetWorkedTime on AttendanceWorkedTime {\n"
            "  id\n"
            "  date\n"
            "  dayType\n"
            "  minutes\n"
            "  multipliedMinutes\n"
            "  pendingMinutes\n"
            "  trackedMinutes\n"
            "  __typename\n"
            "}\n"
            "\n"
            "fragment TimesheetPageShift on AttendanceShift {\n"
            "  id\n"
            "  automaticClockIn\n"
            "  automaticClockOut\n"
            "  clockIn\n"
            "  clockInWithSeconds\n"
            "  clockOut\n"
            "  crossesMidnight\n"
            "  date\n"
            "  employeeId\n"
            "  halfDay\n"
            "  isOvernight\n"
            "  locationType\n"
            "  minutes\n"
            "  observations\n"
            "  periodId\n"
            "  referenceDate\n"
            "  showPlusOneDay\n"
            "  timeSettingsBreakConfiguration {\n"
            "    ...TimesheetTimeSettingsBreakConfiguration\n"
            "    __typename\n"
            "  }\n"
            "  workable\n"
            "  workplace {\n"
            "    ...TimesheetPageWorkplace\n"
            "    __typename\n"
            "  }\n"
            "  __typename\n"
            "}"
        )
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def schedule_day_shifts(employee_id, day, cookie, logger=print):
    shifts = {
        "morning": {
            "clock_in": f"{day}T09:00:00.000Z",
            "clock_out": f"{day}T13:00:00.000Z"
        },
        "lunch_break": {
            "clock_in": f"{day}T13:00:00.000Z",
            "clock_out": f"{day}T14:00:00.000Z"
        },
        "afternoon": {
            "clock_in": f"{day}T15:00:00.000Z",
            "clock_out": f"{day}T18:00:00.000Z"
        }
    }

    day_errors = {}
    logger(f"Scheduling shifts for {day}:")
    for shift_name, times in shifts.items():
        # Extract HH:MM only from the ISO timestamps
        start = times["clock_in"].split("T")[1][:5]
        end = times["clock_out"].split("T")[1][:5]
        # (Optional) Log the shift info in a short format.
        logger(f"  {shift_name}: {start} - {end}")
        result = create_attendance_shift(employee_id, day, times["clock_in"], times["clock_out"], cookie)
        if result.get("data"):
            am = result["data"].get("attendanceMutations", {})
            cas = am.get("createAttendanceShift", {})
            errors = cas.get("errors")
            if errors:
                # Collect errors for this shift.
                msg_list = [error.get("messages", ["Unknown error"])[0] for error in errors]
                day_errors[shift_name] = f"{start} - {end}: " + " | ".join(msg_list)
                logger(f"  Error for {shift_name}: {day_errors[shift_name]}")
    logger(f"Finished scheduling for {day}\n")
    # Return errors dictionary if there were any, otherwise return None.
    return day_errors if day_errors else None

def schedule_month_shifts(employee_id, year, month, cookie, logger=print, stop_event=None):
    num_days = calendar.monthrange(year, month)[1]
    failed_days = {}
    logger(f"Starting scheduling shifts for {year}-{month:02d}...\n")
    for day in range(1, num_days + 1):
        if stop_event is not None and stop_event.is_set():
            logger("Process stopped by user.\n")
            break
        date_obj = datetime.date(year, month, day)
        if date_obj.weekday() < 5:  # Only process Monday to Friday
            day_str = date_obj.isoformat()
            logger(f"Processing {day_str} ({date_obj.strftime('%A')}):")
            errors = schedule_day_shifts(employee_id, day_str, cookie, logger)
            if errors:
                failed_days[day_str] = errors
        else:
            logger(f"Skipping {date_obj.isoformat()} ({date_obj.strftime('%A')}) - Weekend")
    logger("Finished scheduling the month.\n")
    return failed_days

if __name__ == "__main__":
    config = load_config()
    employee_id = config["employee_id"]
    cookie = config["cookie"]
    year = 2025
    month = 2

    month_schedule = schedule_month_shifts(employee_id, year, month, cookie)
    print(json.dumps(month_schedule, indent=2))