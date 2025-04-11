from datetime import time, datetime

def convert_minutes_seconds(minutes_time):
    minutes = int(minutes_time)
    seconds = round((minutes_time - minutes) * 60)
    return time(minute=minutes, second=seconds)


def convert_seconds_to_minutes(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return time(minute=minutes, second=seconds)


def take_the_seconds(str_s):
    current_value = datetime.strptime(str_s, "%H:%M:%S").time()
    return current_value.minute * 60 + current_value.second


def distribute_the_change(data, changed_km, total_seconds):
    
    if str(changed_km) not in data:
        raise KeyError(f"Key {changed_km} not found in pace data: {data}")

    time_for_changed_km = data[str(changed_km)]
    km_in_question = take_the_seconds(time_for_changed_km)

    remaining_seconds = total_seconds - km_in_question
    num_remaining_kms = len(data) - 1

    if num_remaining_kms > 0:
        final_result_sec = remaining_seconds / num_remaining_kms
        new_value = convert_seconds_to_minutes(final_result_sec).strftime("%H:%M:%S")
    else:
        new_value = "00:00:00"

    for km in data.keys():
        if str(km) == str(changed_km):
            data[str(km)] = time_for_changed_km
        else:
            data[str(km)] = new_value 

    return data


def initialize_paces(distance, total_seconds):
    full_kms = int(distance)
    fractional_km = distance - full_kms

    avg_pace_seconds = total_seconds / distance
    data = {}

    for km in range(1, full_kms + 1):
        avg_pace = convert_seconds_to_minutes(
            avg_pace_seconds).strftime("%H:%M:%S")
        data[km] = avg_pace

    if fractional_km > 0:
        fractional_time_seconds = avg_pace_seconds * fractional_km
        fractional_pace = convert_seconds_to_minutes(
            fractional_time_seconds).strftime("%H:%M:%S")
        data[full_kms + 1] = fractional_pace

    return data


def calculate_total_seconds(goal_time):
    validation_of_time = datetime.strptime(goal_time, "%H:%M:%S").time()
    return validation_of_time.hour * 3600 + validation_of_time.minute * 60 + validation_of_time.second