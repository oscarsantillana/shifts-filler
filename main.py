import requests
import json
import calendar
import datetime
import sys
import argparse
from abc import ABC, abstractmethod

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

class TimeProvider(ABC):
    @abstractmethod
    def schedule_day_shifts(self, employee_id, day, auth_data, logger=print):
        """Schedule shifts for a single day"""
        pass

class FactorialProvider(TimeProvider):
    def schedule_day_shifts(self, employee_id, day, auth_data, logger=print):
        cookie = auth_data
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
            result = self._create_attendance_shift(employee_id, day, times["clock_in"], times["clock_out"], cookie)
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

    def _create_attendance_shift(self, employee_id, date, clock_in, clock_out, cookie):
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

class EndaliaProvider(TimeProvider):
    def check_missing_days(self, year, month, auth_token, logger=print):
        """Check which days in the month need to be scheduled (missing or incomplete)"""
        # Get first and last day of the month
        first_day = datetime.date(year, month, 1)
        last_day = datetime.date(year, month, calendar.monthrange(year, month)[1])
        
        # Don't check days in the future - Endalia doesn't allow scheduling future dates
        today = datetime.date.today()
        if last_day > today:
            last_day = today
            logger(f"Limiting check to today ({today.isoformat()}) - cannot schedule future dates")
        
        # If the entire month is in the future, return empty list
        if first_day > today:
            logger(f"Month {year}-{month:02d} is in the future - no days to schedule")
            return []
        
        url = f'https://end03time.endaliahr.com/api/workingdayregisters/me/{first_day.isoformat()}/{last_day.isoformat()}'
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            missing_days = []
            if 'Days' in data:
                for day_info in data['Days']:
                    register_minutes = day_info.get('RegisterMinutes', 0)
                    planned_minutes = day_info.get('PlannedMinutes', 0)
                    day_str = day_info.get('Day', '')
                    
                    # Parse the day string to check if it's not in the future
                    day_date = datetime.date.fromisoformat(day_str)
                    if day_date > today:
                        logger(f"Skipping future date {day_str}")
                        continue
                    
                    # If register minutes don't match planned minutes, the day needs to be scheduled
                    if register_minutes != planned_minutes and planned_minutes > 0:
                        missing_days.append(day_str)
                        logger(f"Day {day_str} needs scheduling: {register_minutes}/{planned_minutes} minutes")
                    elif register_minutes == planned_minutes and planned_minutes > 0:
                        logger(f"Day {day_str} already scheduled: {register_minutes}/{planned_minutes} minutes")
            
            return missing_days
            
        except requests.exceptions.RequestException as e:
            logger(f"Error checking existing days: {e}")
            # If we can't check, assume all workdays need scheduling (but only up to today)
            missing_days = []
            today = datetime.date.today()
            num_days = calendar.monthrange(year, month)[1]
            
            for day in range(1, num_days + 1):
                date_obj = datetime.date(year, month, day)
                # Only include weekdays that are not in the future
                if date_obj.weekday() < 5 and date_obj <= today:
                    missing_days.append(date_obj.isoformat())
            
            logger(f"Fallback: assuming {len(missing_days)} workdays need scheduling (up to today)")
            return missing_days

    def schedule_day_shifts(self, employee_id, day, auth_data, logger=print):
        auth_token = auth_data
        
        # Convert day string to datetime for processing
        day_dt = datetime.datetime.fromisoformat(day)
        
        # Define working schedule - 7:00-16:00 with 11:00-12:00 lunch
        work_start = day_dt.replace(hour=7, minute=0, second=0, microsecond=0)
        work_end = day_dt.replace(hour=16, minute=0, second=0, microsecond=0)
        lunch_start = day_dt.replace(hour=11, minute=0, second=0, microsecond=0)
        lunch_end = day_dt.replace(hour=12, minute=0, second=0, microsecond=0)
        
        logger(f"Scheduling work day for {day}:")
        logger(f"  Work time: 09:00 - 18:00")
        logger(f"  Lunch break: 13:00 - 14:00")
        
        result = self._create_working_day(
            employee_id, 
            day, 
            work_start.isoformat() + "Z",
            work_end.isoformat() + "Z",
            lunch_start.isoformat() + "Z",
            lunch_end.isoformat() + "Z",
            auth_token
        )
        
        if result.get("error"):
            error_msg = f"09:00 - 18:00: {result['error']}"
            logger(f"  Error: {error_msg}")
            return {"work_day": error_msg}
        
        logger(f"Finished scheduling for {day}\n")
        return None

    def _create_working_day(self, employee_id, day, work_start, work_end, lunch_start, lunch_end, auth_token):
        url = 'https://end03time.endaliahr.com/api/workingdayregisters/predictive'
        headers = {
            "Content-Type": "application/json",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {auth_token}",
            "Sec-Fetch-Site": "same-site",
            "Cache-Control": "no-cache",
            "Sec-Fetch-Mode": "cors",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://alea.endaliahr.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=3, i",
            "x-client-tz": "-2.00"
        }

        payload = {
            "Day": day,
            "MainStretchType": {
                "ID": 1,
                "Code": "E/S",
                "Name": "Trabajo",
                "IsStart": True
            },
            "WorkStretchTime": {
                "BeginTime": work_start,
                "EndTime": work_end
            },
            "HasLunch": True,
            "LunchStretchTime": {
                "BeginTime": lunch_start,
                "EndTime": lunch_end
            },
            "BreakStretchTimeList": [],
            "TimezoneOffset": 120,
            "EmpID": None,
            "ComputeMinutes": 480  # 8 hours * 60 minutes
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Check if response has content before trying to parse JSON
            if response.text.strip():
                return response.json()
            else:
                # Empty response body indicates success for Endalia API
                return {"status": "success", "message": "Working day created successfully"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def get_provider(provider_type, config):
    """Factory function to get the appropriate time provider"""
    if provider_type.lower() == "factorial":
        return FactorialProvider(), config.get("cookie")
    elif provider_type.lower() == "endalia":
        return EndaliaProvider(), config.get("auth_token")
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

def schedule_month_shifts(provider, employee_id, year, month, auth_data, logger=print, stop_event=None):
    num_days = calendar.monthrange(year, month)[1]
    failed_days = {}
    logger(f"Starting scheduling shifts for {year}-{month:02d}...\n")
    
    # For Endalia, check which days are missing first
    if isinstance(provider, EndaliaProvider):
        logger("Checking which days need to be scheduled...")
        missing_days = provider.check_missing_days(year, month, auth_data, logger)
        logger(f"Found {len(missing_days)} days that need scheduling\n")
        
        # Only process missing days
        for day_str in missing_days:
            if stop_event is not None and stop_event.is_set():
                logger("Process stopped by user.\n")
                break
            date_obj = datetime.date.fromisoformat(day_str)
            logger(f"Processing {day_str} ({date_obj.strftime('%A')}):")
            errors = provider.schedule_day_shifts(employee_id, day_str, auth_data, logger)
            if errors:
                failed_days[day_str] = errors
    else:
        # For other providers (Factorial), process all weekdays
        for day in range(1, num_days + 1):
            if stop_event is not None and stop_event.is_set():
                logger("Process stopped by user.\n")
                break
            date_obj = datetime.date(year, month, day)
            if date_obj.weekday() < 5:  # Only process Monday to Friday
                day_str = date_obj.isoformat()
                logger(f"Processing {day_str} ({date_obj.strftime('%A')}):")
                errors = provider.schedule_day_shifts(employee_id, day_str, auth_data, logger)
                if errors:
                    failed_days[day_str] = errors
            else:
                logger(f"Skipping {date_obj.isoformat()} ({date_obj.strftime('%A')}) - Weekend")
    
    logger("Finished scheduling the month.\n")
    return failed_days

# Legacy functions for backward compatibility
def schedule_day_shifts(employee_id, day, cookie, logger=print):
    """Legacy function - use FactorialProvider instead"""
    provider = FactorialProvider()
    return provider.schedule_day_shifts(employee_id, day, cookie, logger)

def create_attendance_shift(employee_id, date, clock_in, clock_out, cookie):
    """Legacy function - use FactorialProvider instead"""
    provider = FactorialProvider()
    return provider._create_attendance_shift(employee_id, date, clock_in, clock_out, cookie)

def get_month_year_from_args():
    """Get month and year from command line arguments or user input"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Schedule time tracking shifts")
    parser.add_argument("-m", "--month", type=int, help="Month (1-12)")
    parser.add_argument("-y", "--year", type=int, help="Year (e.g., 2025)")
    parser.add_argument("--interactive", action="store_true", help="Use interactive mode to input month/year")
    
    args = parser.parse_args()
    
    # If interactive mode is requested or no arguments provided
    if args.interactive or (args.month is None and args.year is None):
        print("Interactive mode - Enter the month and year to schedule:")
        
        # Get current date as default
        current_date = datetime.date.today()
        
        # Get month
        while True:
            try:
                month_input = input(f"Month (1-12) [default: {current_date.month}]: ").strip()
                if not month_input:
                    month = current_date.month
                else:
                    month = int(month_input)
                if 1 <= month <= 12:
                    break
                else:
                    print("Month must be between 1 and 12")
            except ValueError:
                print("Please enter a valid number for month")
        
        # Get year
        while True:
            try:
                year_input = input(f"Year [default: {current_date.year}]: ").strip()
                if not year_input:
                    year = current_date.year
                else:
                    year = int(year_input)
                if year >= 2020:  # Reasonable minimum year
                    break
                else:
                    print("Year must be 2020 or later")
            except ValueError:
                print("Please enter a valid number for year")
        
        return year, month
    
    # Use provided arguments with defaults
    year = args.year if args.year is not None else datetime.date.today().year
    month = args.month if args.month is not None else datetime.date.today().month
    
    # Validate arguments
    if not (1 <= month <= 12):
        print("Error: Month must be between 1 and 12")
        sys.exit(1)
    
    if year < 2020:
        print("Error: Year must be 2020 or later")
        sys.exit(1)
    
    return year, month

if __name__ == "__main__":
    config = load_config()
    employee_id = config["employee_id"]
    
    # Determine provider type based on config
    provider_type = config.get("provider", "factorial")  # Default to factorial for backward compatibility
    
    try:
        provider, auth_data = get_provider(provider_type, config)
        year, month = get_month_year_from_args()
        
        print(f"Scheduling shifts for {calendar.month_name[month]} {year}")
        print(f"Using provider: {provider_type}")
        print()

        month_schedule = schedule_month_shifts(provider, employee_id, year, month, auth_data)
        
        if month_schedule:
            print("\nErrors encountered:")
            print(json.dumps(month_schedule, indent=2))
        else:
            print("\nAll shifts scheduled successfully!")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)