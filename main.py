from datetime import datetime, timedelta, timezone  # 날짜 계산과 발리 고정 시간대를 만들기 위해 가져옵니다.
from statistics import mean  # 추천 구간의 평균 파도 높이, 주기, 풍속을 계산하기 위해 가져옵니다.
from urllib.parse import urlencode  # API 파라미터를 URL 형식으로 안전하게 조립하기 위해 가져옵니다.
from zoneinfo import ZoneInfo  # 발리 현지 시간대를 적용하기 위해 가져옵니다.

import requests  # Open-Meteo API를 호출하기 위해 가져옵니다.


LATITUDE = -8.711  # 발리 레기안 해변 라인업 기준 위도입니다.
LONGITUDE = 115.166  # 발리 레기안 해변 라인업 기준 경도입니다.
BALI_TIMEZONE = "Asia/Makassar"  # 발리 현지 시간대 이름입니다.
BALI_FIXED_TIMEZONE = timezone(timedelta(hours=8))  # 시간대 데이터가 없을 때 사용할 발리 UTC+8 고정 시간대입니다.
MAX_WIND_SPEED_KMH = 25.0  # 풍속이 이 값보다 강하면 서핑 품질이 떨어진다고 판단합니다.
OFFSHORE_MIN_DEGREE = 45.0  # 레기안 기준 동풍 계열 오프쇼어 최소 풍향각입니다.
OFFSHORE_MAX_DEGREE = 135.0  # 레기안 기준 동풍 계열 오프쇼어 최대 풍향각입니다.
MIN_WAVE_PERIOD_SECONDS = 7.0  # 서핑 가능한 너울로 판단할 최소 파도 주기입니다.
MID_TIDE_RANGE_RATIO = 0.25  # 최저 조수와 최고 조수 사이 중간 수위에서 앞뒤로 허용할 비율입니다.


def get_bali_today():  # 발리 현지 기준 오늘 날짜를 구하는 함수입니다.
    try:  # 운영체제에 Asia/Makassar 시간대 데이터가 있는지 시도합니다.
        bali_timezone = ZoneInfo(BALI_TIMEZONE)  # 시간대 데이터가 있으면 정확한 발리 시간대를 사용합니다.
    except Exception:  # Windows에서 tzdata가 없으면 예외가 날 수 있습니다.
        bali_timezone = BALI_FIXED_TIMEZONE  # 발리는 UTC+8이므로 고정 시간대로 대신 계산합니다.
    return datetime.now(bali_timezone).date()  # 발리 현지 기준 오늘 날짜만 반환합니다.


def build_url(base_url, params):  # 기본 URL과 파라미터를 합쳐 최종 API 주소를 만드는 함수입니다.
    return f"{base_url}?{urlencode(params)}"  # 파라미터를 안전하게 인코딩해서 URL 뒤에 붙입니다.


def fetch_json(url):  # API를 호출해서 JSON 데이터를 받는 함수입니다.
    response = requests.get(url, timeout=20)  # API 서버에 GET 요청을 보내고 최대 20초 기다립니다.
    response.raise_for_status()  # HTTP 오류가 있으면 즉시 에러를 발생시킵니다.
    return response.json()  # 응답 본문을 JSON 딕셔너리로 변환해 반환합니다.


def fetch_marine_data(start_date, end_date):  # 지정한 기간의 파도와 조수 데이터를 가져오는 함수입니다.
    params = {  # Open-Meteo Marine API에 전달할 파라미터입니다.
        "latitude": LATITUDE,  # 요청 좌표의 위도입니다.
        "longitude": LONGITUDE,  # 요청 좌표의 경도입니다.
        "hourly": "wave_height,wave_period,sea_level_height_msl",  # 시간별 파고, 파도 주기, 조수 수위를 요청합니다.
        "timezone": BALI_TIMEZONE,  # 응답 시간을 발리 현지 시간으로 받습니다.
        "start_date": start_date.isoformat(),  # 조회 시작일을 설정합니다.
        "end_date": end_date.isoformat(),  # 조회 종료일을 설정합니다.
        "length_unit": "metric",  # 파도 높이를 미터 단위로 받습니다.
        "cell_selection": "sea",  # 좌표 주변에서 바다 격자를 우선 선택합니다.
    }  # 해양 API 파라미터 정의를 끝냅니다.
    url = build_url("https://marine-api.open-meteo.com/v1/marine", params)  # 실제 호출할 해양 API 주소를 만듭니다.
    return fetch_json(url), url  # API 응답 데이터와 호출 URL을 함께 반환합니다.


def fetch_wind_data(start_date, end_date):  # 지정한 기간의 풍속과 풍향 데이터를 가져오는 함수입니다.
    params = {  # Open-Meteo Forecast API에 전달할 파라미터입니다.
        "latitude": LATITUDE,  # 요청 좌표의 위도입니다.
        "longitude": LONGITUDE,  # 요청 좌표의 경도입니다.
        "hourly": "wind_speed_10m,wind_direction_10m",  # 시간별 10m 풍속과 풍향을 요청합니다.
        "timezone": BALI_TIMEZONE,  # 응답 시간을 발리 현지 시간으로 받습니다.
        "start_date": start_date.isoformat(),  # 조회 시작일을 설정합니다.
        "end_date": end_date.isoformat(),  # 조회 종료일을 설정합니다.
        "wind_speed_unit": "kmh",  # 풍속을 km/h 단위로 받습니다.
    }  # 바람 API 파라미터 정의를 끝냅니다.
    url = build_url("https://api.open-meteo.com/v1/forecast", params)  # 실제 호출할 날씨 API 주소를 만듭니다.
    return fetch_json(url), url  # API 응답 데이터와 호출 URL을 함께 반환합니다.


def merge_hourly_data(marine_json, wind_json):  # 해양 데이터와 바람 데이터를 시간 기준으로 합치는 함수입니다.
    marine = marine_json["hourly"]  # 해양 API의 시간별 데이터 묶음을 꺼냅니다.
    wind = wind_json["hourly"]  # 날씨 API의 시간별 데이터 묶음을 꺼냅니다.
    wind_index = {time_text: index for index, time_text in enumerate(wind["time"])}  # 바람 데이터를 시간으로 빠르게 찾기 위한 인덱스입니다.
    rows = []  # 합쳐진 시간별 데이터를 담을 리스트입니다.
    for marine_index, time_text in enumerate(marine["time"]):  # 해양 데이터의 각 시간대를 순서대로 확인합니다.
        if time_text not in wind_index:  # 같은 시간이 바람 데이터에 없으면 건너뜁니다.
            continue  # 병합할 수 없는 시간대는 제외합니다.
        wind_i = wind_index[time_text]  # 같은 시간대의 바람 데이터 위치를 찾습니다.
        rows.append(  # 시간별 판단에 필요한 값을 하나의 딕셔너리로 추가합니다.
            {  # 한 시간대의 모든 핵심 데이터를 담습니다.
                "time": time_text,  # 발리 현지 시간 문자열입니다.
                "date": datetime.fromisoformat(time_text).date(),  # 날짜별 조수 계산을 위한 날짜 값입니다.
                "wave_height": marine["wave_height"][marine_index],  # 해당 시간의 파도 높이입니다.
                "wave_period": marine["wave_period"][marine_index],  # 해당 시간의 파도 주기입니다.
                "tide": marine["sea_level_height_msl"][marine_index],  # 해당 시간의 조수 수위입니다.
                "wind_speed": wind["wind_speed_10m"][wind_i],  # 해당 시간의 풍속입니다.
                "wind_direction": wind["wind_direction_10m"][wind_i],  # 해당 시간의 풍향각입니다.
            }  # 시간별 딕셔너리 작성을 끝냅니다.
        )  # 시간별 딕셔너리를 리스트에 추가합니다.
    return rows  # 병합된 시간별 데이터를 반환합니다.


def wind_direction_korean(degree):  # 풍향각을 한글 방위로 바꾸는 함수입니다.
    directions = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]  # 8방위 이름을 준비합니다.
    return directions[round(degree / 45) % 8]  # 풍향각에 가장 가까운 8방위 이름을 반환합니다.


def period_description(period):  # 파도 주기에 대한 설명을 만드는 함수입니다.
    if period is None:  # 파도 주기 데이터가 없는 경우입니다.
        return "데이터 없음"  # 데이터가 없다고 표시합니다.
    if 7 <= period <= 11:  # 7초부터 11초는 부드럽고 다루기 좋은 주기입니다.
        return "가장 이상적이고 부드러운 파도"  # 요청한 문구를 반환합니다.
    if period >= 12:  # 12초 이상은 힘이 강한 장주기 너울입니다.
        return "강한 너울: 라인업 돌파 시 강력한 패들링 스태미나 필요"  # 요청한 경고를 반환합니다.
    return "주기가 짧아 힘이 약한 파도"  # 7초 미만은 서핑 품질이 낮다고 설명합니다.


def height_level(row):  # 파도 높이 기준으로 초보, 중급, 고수 난이도를 정하는 함수입니다.
    height = row["wave_height"]  # 판단할 파도 높이를 꺼냅니다.
    if height is None:  # 파도 높이 데이터가 없는 경우입니다.
        return "판단불가"  # 난이도를 판단할 수 없다고 반환합니다.
    if height <= 1.0:  # 1m 이하는 사용자가 요청한 초보 기준입니다.
        return "초보"  # 초보에게 맞는 파도 높이라고 반환합니다.
    if height < 2.0:  # 1m 초과 2m 미만은 중급 기준입니다.
        return "중급"  # 중급자에게 맞는 파도 높이라고 반환합니다.
    return "고수"  # 2m 이상은 고수용으로 반환합니다.


def judge_hour(row, mid_tide, tide_range):  # 한 시간대가 서핑하기 좋은지 종합 평가하는 함수입니다.
    wind_direction = row["wind_direction"]  # 풍향각을 꺼냅니다.
    wind_speed = row["wind_speed"]  # 풍속을 꺼냅니다.
    wave_period = row["wave_period"]  # 파도 주기를 꺼냅니다.
    tide = row["tide"]  # 조수 수위를 꺼냅니다.
    row["offshore_ok"] = wind_direction is not None and OFFSHORE_MIN_DEGREE <= wind_direction <= OFFSHORE_MAX_DEGREE and wind_speed <= MAX_WIND_SPEED_KMH  # 오프쇼어 방향이며 풍속이 너무 강하지 않은지 판단합니다.
    row["period_ok"] = wave_period is not None and wave_period >= MIN_WAVE_PERIOD_SECONDS  # 파도 주기가 7초 이상인지 판단합니다.
    row["mid_tide_ok"] = tide is not None and abs(tide - mid_tide) <= tide_range  # 조수가 미드타이드 근처인지 판단합니다.
    row["all_ok"] = row["offshore_ok"] and row["period_ok"] and row["mid_tide_ok"]  # 핵심 세 조건이 모두 맞는지 판단합니다.
    row["level"] = height_level(row)  # 파도 높이 기준 난이도를 계산합니다.
    passed_count = sum([row["offshore_ok"], row["period_ok"], row["mid_tide_ok"]])  # 세 조건 중 몇 개가 통과했는지 셉니다.
    if row["all_ok"]:  # 세 조건이 모두 맞는 경우입니다.
        row["surf_quality"] = "좋음"  # 서핑하기 좋은 시간대로 표시합니다.
    elif passed_count >= 2:  # 조건 두 개만 맞는 경우입니다.
        row["surf_quality"] = "애매"  # 서핑은 가능하지만 완벽하지 않다고 표시합니다.
    else:  # 조건이 하나 이하로 맞는 경우입니다.
        row["surf_quality"] = "나쁨"  # 추천하기 어렵다고 표시합니다.
    if not row["offshore_ok"]:  # 바람 조건이 문제인지 확인합니다.
        row["reason"] = "바람 불리"  # 바람 방향 또는 풍속이 좋지 않다고 표시합니다.
    elif not row["period_ok"]:  # 파도 주기 조건이 문제인지 확인합니다.
        row["reason"] = "주기 짧음"  # 파도 주기가 짧다고 표시합니다.
    elif not row["mid_tide_ok"]:  # 조수 조건이 문제인지 확인합니다.
        row["reason"] = "조수 애매"  # 미드타이드가 아니라고 표시합니다.
    else:  # 모든 조건이 좋은 경우입니다.
        row["reason"] = "조건 양호"  # 전반적으로 조건이 좋다고 표시합니다.


def judge_all_rows(rows):  # 전체 시간대 데이터를 날짜별로 나눠 조수 기준과 평가를 적용하는 함수입니다.
    tide_info_by_date = {}  # 날짜별 최저, 최고, 중간 조수 정보를 저장할 딕셔너리입니다.
    dates = sorted({row["date"] for row in rows})  # 데이터에 포함된 날짜 목록을 정렬합니다.
    for day in dates:  # 각 날짜를 하나씩 처리합니다.
        day_rows = [row for row in rows if row["date"] == day]  # 해당 날짜의 24시간 데이터를 모읍니다.
        tide_values = [row["tide"] for row in day_rows if row["tide"] is not None]  # 조수 수위가 있는 값만 모읍니다.
        low_tide = min(tide_values)  # 해당 날짜의 최저 조수 수위를 계산합니다.
        high_tide = max(tide_values)  # 해당 날짜의 최고 조수 수위를 계산합니다.
        mid_tide = (low_tide + high_tide) / 2  # 최저와 최고 사이의 중간 조수 수위를 계산합니다.
        tide_range = (high_tide - low_tide) * MID_TIDE_RANGE_RATIO  # 중간 수위에서 허용할 전후 범위를 계산합니다.
        tide_info_by_date[day] = (low_tide, high_tide, mid_tide)  # 날짜별 조수 기준을 저장합니다.
        for row in day_rows:  # 해당 날짜의 각 시간대를 평가합니다.
            judge_hour(row, mid_tide, tide_range)  # 바람, 주기, 조수, 난이도, 좋고 나쁨을 계산합니다.
    return tide_info_by_date  # 날짜별 조수 정보를 반환합니다.


def find_best_segments(day_rows):  # 하루 안에서 세 조건을 모두 만족하는 연속 구간을 찾는 함수입니다.
    segments = []  # 추천 후보 구간을 담을 리스트입니다.
    current = []  # 현재 이어지는 통과 구간을 담을 리스트입니다.
    for row in day_rows:  # 하루의 시간대 데이터를 순서대로 확인합니다.
        if row["all_ok"]:  # 해당 시간이 세 조건을 모두 통과했는지 확인합니다.
            current.append(row)  # 통과했다면 현재 구간에 추가합니다.
        elif current:  # 통과하지 않았고 이어진 구간이 있으면 구간이 끝난 것입니다.
            segments.append(current)  # 끝난 구간을 후보 목록에 저장합니다.
            current = []  # 다음 구간을 찾기 위해 현재 구간을 비웁니다.
    if current:  # 마지막 시간까지 이어진 구간이 있으면 저장합니다.
        segments.append(current)  # 마지막 후보 구간을 추가합니다.
    if not segments:  # 통과 구간이 하나도 없는 경우입니다.
        return None  # 추천 구간 없음으로 반환합니다.
    return max(segments, key=segment_score)  # 가장 점수가 높은 구간을 반환합니다.


def segment_score(segment):  # 추천 구간끼리 비교하기 위한 점수를 계산하는 함수입니다.
    length_score = len(segment) * 1000  # 긴 연속 시간대일수록 높은 점수를 줍니다.
    ideal_period_score = sum(1 for row in segment if 7 <= row["wave_period"] <= 11) * 50  # 7~11초 주기가 많을수록 점수를 더합니다.
    calm_wind_score = max(0, 50 - mean(row["wind_speed"] for row in segment))  # 풍속이 약할수록 점수를 더합니다.
    height_fit_score = sum(30 for row in segment if row["wave_height"] is not None and row["wave_height"] <= 2.0)  # 초보와 중급도 접근 가능한 높이에 가산점을 줍니다.
    return length_score + ideal_period_score + calm_wind_score + height_fit_score  # 전체 추천 점수를 반환합니다.


def time_text(time_value):  # ISO 시간 문자열을 24시간제 시각으로 바꾸는 함수입니다.
    return datetime.fromisoformat(time_value).strftime("%H:%M")  # 예를 들어 08:00 형식으로 반환합니다.


def segment_text(segment):  # 추천 구간을 "08:00 ~ 10:00" 형식으로 만드는 함수입니다.
    start = datetime.fromisoformat(segment[0]["time"])  # 구간의 시작 시간을 datetime으로 바꿉니다.
    end = datetime.fromisoformat(segment[-1]["time"]) + timedelta(hours=1)  # 마지막 시간대가 끝나는 시각을 계산합니다.
    return f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"  # 시작과 끝을 보기 좋은 문자열로 반환합니다.


def pass_text(value):  # True 또는 False를 한글 통과 표시로 바꾸는 함수입니다.
    return "통과" if value else "탈락"  # 참이면 통과, 거짓이면 탈락을 반환합니다.


def print_day_report(day, day_rows, tide_info, best_segment):  # 하루치 시간별 표와 추천 요약을 출력하는 함수입니다.
    low_tide, high_tide, mid_tide = tide_info  # 날짜별 조수 기준값을 꺼냅니다.
    print("=" * 122)  # 날짜 구분선을 출력합니다.
    print(f"기준일: {day.month}월 {day.day}일")  # 요청한 기준일을 월일 형식으로 출력합니다.
    print(f"조수 기준: 최저 {low_tide:.2f}m / 최고 {high_tide:.2f}m / 중간 {mid_tide:.2f}m")  # 미드타이드 계산 기준을 출력합니다.
    print("-" * 122)  # 표 위쪽 구분선을 출력합니다.
    print(f"{'시간':<6} {'파고':>7} {'주기':>7} {'풍향':>10} {'풍속':>10} {'조수':>8} {'평가':>6} {'난이도':>6} {'바람':>6} {'주기':>6} {'조수':>6} {'이유':>10}")  # 표 헤더를 출력합니다.
    print("-" * 122)  # 표 헤더 아래 구분선을 출력합니다.
    for row in day_rows:  # 해당 날짜의 24시간 데이터를 한 줄씩 출력합니다.
        wave_height = f"{row['wave_height']:.2f}m" if row["wave_height"] is not None else "없음"  # 파도 높이를 문자열로 만듭니다.
        wave_period = f"{row['wave_period']:.1f}초" if row["wave_period"] is not None else "없음"  # 파도 주기를 문자열로 만듭니다.
        wind_direction = f"{wind_direction_korean(row['wind_direction'])}({row['wind_direction']:.0f}도)" if row["wind_direction"] is not None else "없음"  # 풍향을 한글과 각도로 표시합니다.
        wind_speed = f"{row['wind_speed']:.1f}km/h" if row["wind_speed"] is not None else "없음"  # 풍속을 문자열로 만듭니다.
        tide = f"{row['tide']:.2f}m" if row["tide"] is not None else "없음"  # 조수 수위를 문자열로 만듭니다.
        print(f"{time_text(row['time']):<6} {wave_height:>7} {wave_period:>7} {wind_direction:>10} {wind_speed:>10} {tide:>8} {row['surf_quality']:>6} {row['level']:>6} {pass_text(row['offshore_ok']):>6} {pass_text(row['period_ok']):>6} {pass_text(row['mid_tide_ok']):>6} {row['reason']:>10}")  # 한 시간대의 모든 판단 결과를 출력합니다.
    print("-" * 122)  # 표 아래 구분선을 출력합니다.
    if best_segment is None:  # 추천 구간이 없는지 확인합니다.
        print("제일 추천하는 시간대: 세 조건을 모두 만족하는 시간이 없습니다.")  # 추천 구간이 없다고 출력합니다.
        return  # 해당 날짜 리포트를 마칩니다.
    avg_height = mean(row["wave_height"] for row in best_segment if row["wave_height"] is not None)  # 추천 구간의 평균 파도 높이를 계산합니다.
    avg_period = mean(row["wave_period"] for row in best_segment if row["wave_period"] is not None)  # 추천 구간의 평균 파도 주기를 계산합니다.
    avg_wind = mean(row["wind_speed"] for row in best_segment if row["wind_speed"] is not None)  # 추천 구간의 평균 풍속을 계산합니다.
    avg_direction = wind_direction_korean(mean(row["wind_direction"] for row in best_segment if row["wind_direction"] is not None))  # 추천 구간의 대표 풍향을 계산합니다.
    best_level = height_level({"wave_height": avg_height})  # 추천 구간의 평균 파고 기준 난이도를 계산합니다.
    print("제일 추천하는 시간대")  # 추천 요약 제목을 출력합니다.
    print(f"Best Time: {segment_text(best_segment)}")  # 가장 좋은 연속 시간대를 출력합니다.
    print(f"추천 난이도: {best_level}")  # 초보, 중급, 고수 중 어떤 난이도인지 출력합니다.
    print(f"예상 파도 높이: 평균 {avg_height:.2f}m")  # 평균 파도 높이를 출력합니다.
    print(f"예상 파도 주기: 평균 {avg_period:.1f}초, {period_description(avg_period)}")  # 평균 주기와 설명을 출력합니다.
    print(f"예상 바람: {avg_direction} 계열 오프쇼어, 평균 {avg_wind:.1f}km/h")  # 대표 풍향과 평균 풍속을 출력합니다.
    if any(row["wave_period"] is not None and row["wave_period"] >= 12 for row in best_segment):  # 강한 장주기 너울이 포함됐는지 확인합니다.
        print("추가 경고: 파도의 힘(Swell Power)이 매우 강하므로, 라인업 돌파 시 강력한 패들링 스태미나가 요구됨")  # 요청한 강한 너울 경고를 출력합니다.


def print_report(start_date, end_date, rows, tide_info_by_date, marine_url, wind_url):  # 전체 3일치 리포트를 출력하는 함수입니다.
    print("=" * 122)  # 전체 리포트 상단 구분선을 출력합니다.
    print("발리 레기안 해변 3일 서핑 추천 리포트")  # 전체 리포트 제목을 출력합니다.
    print("=" * 122)  # 제목 아래 구분선을 출력합니다.
    print(f"조회 기간: {start_date.month}월 {start_date.day}일 ~ {end_date.month}월 {end_date.day}일")  # 오늘, 내일, 모레 날짜 범위를 출력합니다.
    print(f"좌표: 위도 {LATITUDE}, 경도 {LONGITUDE}")  # 실제 API 호출에 사용한 좌표를 출력합니다.
    print(f"시간대: 발리 현지 시간({BALI_TIMEZONE})")  # 출력 시간이 발리 현지 시간임을 안내합니다.
    print(f"해양 API 주소: {marine_url}")  # 검증 가능한 해양 API 주소를 출력합니다.
    print(f"바람 API 주소: {wind_url}")  # 검증 가능한 바람 API 주소를 출력합니다.
    print("난이도 기준: 초보 1m 이하 / 중급 2m 이하 / 고수 2m 이상, 단 바람 방향과 파도 주기와 조수 조건을 함께 반영")  # 난이도 기준을 출력합니다.
    print("좋음 기준: 오프쇼어 바람, 7초 이상 파도 주기, 미드타이드 조건을 모두 통과")  # 좋음 평가 기준을 출력합니다.
    all_best_segments = []  # 전체 3일 중 최고 추천을 찾기 위한 리스트입니다.
    for day in sorted(tide_info_by_date):  # 날짜별로 리포트를 출력합니다.
        day_rows = [row for row in rows if row["date"] == day]  # 해당 날짜의 시간별 데이터를 모읍니다.
        best_segment = find_best_segments(day_rows)  # 해당 날짜의 최고 추천 구간을 찾습니다.
        if best_segment is not None:  # 추천 구간이 있는 날짜인지 확인합니다.
            all_best_segments.append(best_segment)  # 전체 최고 후보에 추가합니다.
        print_day_report(day, day_rows, tide_info_by_date[day], best_segment)  # 하루치 상세 리포트를 출력합니다.
    print("=" * 122)  # 전체 요약 구분선을 출력합니다.
    if not all_best_segments:  # 3일 전체에서 추천 구간이 하나도 없는지 확인합니다.
        print("전체 최고 추천: 3일 동안 세 조건을 모두 만족하는 시간대가 없습니다.")  # 전체 추천 없음으로 출력합니다.
        return  # 전체 리포트를 마칩니다.
    best_overall = max(all_best_segments, key=segment_score)  # 날짜별 추천 구간 중 최고 점수 구간을 고릅니다.
    best_day = best_overall[0]["date"]  # 전체 최고 추천 구간의 날짜를 가져옵니다.
    print("전체 최고 추천")  # 전체 추천 제목을 출력합니다.
    print(f"{best_day.month}월 {best_day.day}일 {segment_text(best_overall)}")  # 전체 최고 추천 날짜와 시간을 출력합니다.
    print(f"난이도: {height_level({'wave_height': mean(row['wave_height'] for row in best_overall if row['wave_height'] is not None)})}")  # 전체 최고 추천 구간의 평균 파고 기준 난이도를 출력합니다.
    print("=" * 122)  # 전체 리포트 하단 구분선을 출력합니다.


def main():  # 프로그램의 전체 실행 흐름을 담당하는 함수입니다.
    start_date = get_bali_today()  # 발리 현지 기준 오늘 날짜를 구합니다.
    end_date = start_date + timedelta(days=2)  # 오늘부터 모레까지 총 3일 조회하도록 종료일을 계산합니다.
    marine_json, marine_url = fetch_marine_data(start_date, end_date)  # 3일치 해양 데이터를 가져옵니다.
    wind_json, wind_url = fetch_wind_data(start_date, end_date)  # 3일치 바람 데이터를 가져옵니다.
    rows = merge_hourly_data(marine_json, wind_json)  # 해양 데이터와 바람 데이터를 시간별로 합칩니다.
    tide_info_by_date = judge_all_rows(rows)  # 날짜별 조수 기준과 시간별 서핑 평가를 계산합니다.
    print_report(start_date, end_date, rows, tide_info_by_date, marine_url, wind_url)  # 최종 한국어 콘솔 리포트를 출력합니다.


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만 아래 코드를 실행합니다.
    main()  # 메인 함수를 호출해 프로그램을 시작합니다.
