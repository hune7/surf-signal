const MIN_WAVE_PERIOD_SECONDS = 7;
const MID_TIDE_RANGE_RATIO = 0.25;

const SPOTS = {
  legian: {
    key: "legian",
    shortName: "발리 레기안",
    badge: "Legian Beach",
    title: "Legian Surf Signal",
    description: "발리 레기안 해변 라인업 기준",
    heroCopy: "서쪽을 바라보는 레기안 기준, 동풍 오프쇼어와 미드 타이드를 조합해 오늘부터 모레까지 입수 타이밍을 잡아줍니다.",
    latitude: -8.711,
    longitude: 115.166,
    timezone: "Asia/Makassar",
    offshoreMinDegree: 45,
    offshoreMaxDegree: 135,
    maxWindSpeedKmh: 25,
    offshoreText: "동풍 계열 45도~135도",
    idealPeriodText: "가장 이상적이고 부드러운 파도",
  },
  songjeong: {
    key: "songjeong",
    shortName: "송정 라스트웨이브",
    badge: "Songjeong Last Wave",
    title: "Songjeong Surf Signal",
    description: "송정해수욕장 라스트웨이브 서핑샵 앞바다 기준",
    heroCopy: "남동쪽을 바라보는 송정 라스트웨이브 앞 기준, 서풍~북풍 오프쇼어와 미드 타이드를 조합해 입수 타이밍을 잡아줍니다.",
    latitude: 35.1791,
    longitude: 129.2,
    timezone: "Asia/Seoul",
    offshoreMinDegree: 270,
    offshoreMaxDegree: 360,
    maxWindSpeedKmh: 25.2,
    offshoreText: "서풍~북풍 계열 270도~360도",
    idealPeriodText: "9.6피트 롱보드나 7.6피트 미드랭스로 여유로운 라이딩을 즐기기 가장 이상적이고 부드러운 파도",
  },
};

const state = {
  activeSpotKey: "legian",
  rows: [],
  tideInfoByDate: new Map(),
  bestSegments: [],
};

const elements = {
  spotBadge: document.querySelector("#spotBadge"),
  clock: document.querySelector("#clock"),
  heroTitle: document.querySelector("#heroTitle"),
  heroCopy: document.querySelector("#heroCopy"),
  refreshButton: document.querySelector("#refreshButton"),
  overallBest: document.querySelector("#overallBest"),
  overallDetail: document.querySelector("#overallDetail"),
  coordinateText: document.querySelector("#coordinateText"),
  spotDescription: document.querySelector("#spotDescription"),
  ruleSummary: document.querySelector("#ruleSummary"),
  forecastLabel: document.querySelector("#forecastLabel"),
  updatedAt: document.querySelector("#updatedAt"),
  loading: document.querySelector("#loading"),
  error: document.querySelector("#error"),
  dayTabs: document.querySelector("#dayTabs"),
  dayPanels: document.querySelector("#dayPanels"),
  spotButtons: document.querySelectorAll(".spot-button"),
};

function activeSpot() {
  return SPOTS[state.activeSpotKey];
}

function getSpotNowParts(spot) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: spot.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    year: Number(value.year),
    month: Number(value.month),
    day: Number(value.day),
    hour: Number(value.hour),
    minute: Number(value.minute),
    second: Number(value.second),
  };
}

function formatDateKey(date) {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(dateKey, amount) {
  const [year, month, day] = dateKey.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day + amount));
  return formatDateKey(date);
}

function getDateRange(spot) {
  const now = getSpotNowParts(spot);
  const today = `${now.year}-${String(now.month).padStart(2, "0")}-${String(now.day).padStart(2, "0")}`;
  return {
    startDate: today,
    endDate: addDays(today, 2),
  };
}

function updateClock() {
  const spot = activeSpot();
  const now = new Intl.DateTimeFormat("ko-KR", {
    timeZone: spot.timezone,
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
  elements.clock.textContent = `${spot.shortName} 현재 ${now}`;
}

function buildUrl(baseUrl, params) {
  return `${baseUrl}?${new URLSearchParams(params).toString()}`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API 오류: ${response.status}`);
  }
  return response.json();
}

async function fetchForecast(spot, startDate, endDate) {
  const marineUrl = buildUrl("https://marine-api.open-meteo.com/v1/marine", {
    latitude: spot.latitude,
    longitude: spot.longitude,
    hourly: "wave_height,wave_period,sea_level_height_msl",
    timezone: spot.timezone,
    start_date: startDate,
    end_date: endDate,
    length_unit: "metric",
    cell_selection: "sea",
  });

  const windUrl = buildUrl("https://api.open-meteo.com/v1/forecast", {
    latitude: spot.latitude,
    longitude: spot.longitude,
    hourly: "wind_speed_10m,wind_direction_10m",
    timezone: spot.timezone,
    start_date: startDate,
    end_date: endDate,
    wind_speed_unit: "kmh",
  });

  const [marineJson, windJson] = await Promise.all([fetchJson(marineUrl), fetchJson(windUrl)]);
  return { marineJson, windJson };
}

function mergeHourlyData(marineJson, windJson) {
  const windIndex = new Map(windJson.hourly.time.map((time, index) => [time, index]));
  return marineJson.hourly.time
    .map((time, index) => {
      const windI = windIndex.get(time);
      if (windI === undefined) return null;
      return {
        time,
        date: time.slice(0, 10),
        waveHeight: marineJson.hourly.wave_height[index],
        wavePeriod: marineJson.hourly.wave_period[index],
        tide: marineJson.hourly.sea_level_height_msl[index],
        windSpeed: windJson.hourly.wind_speed_10m[windI],
        windDirection: windJson.hourly.wind_direction_10m[windI],
      };
    })
    .filter(Boolean);
}

function windDirectionKorean(degree) {
  const directions = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"];
  return directions[Math.round(degree / 45) % 8];
}

function periodDescription(period, spot) {
  if (period === null || period === undefined) return "데이터 없음";
  if (period >= 7 && period <= 11) return spot.idealPeriodText;
  if (period >= 12) return "파도의 힘(Swell Power)이 매우 강하므로, 라인업 돌파 시 강력한 패들링 스태미나가 요구됨";
  return "주기가 짧아 힘이 약한 파도";
}

function heightLevel(row) {
  if (row.waveHeight === null || row.waveHeight === undefined) return "판단불가";
  if (row.waveHeight <= 1) return "초보";
  if (row.waveHeight < 2) return "중급";
  return "고수";
}

function levelClass(level) {
  if (level === "초보") return "level-beginner";
  if (level === "중급") return "level-intermediate";
  if (level === "고수") return "level-advanced";
  return "";
}

function isOffshore(row, spot) {
  const directionOk = row.windDirection >= spot.offshoreMinDegree && row.windDirection <= spot.offshoreMaxDegree;
  return row.windDirection !== null && directionOk && row.windSpeed <= spot.maxWindSpeedKmh;
}

function judgeRows(rows, spot) {
  state.tideInfoByDate.clear();
  const dates = [...new Set(rows.map((row) => row.date))].sort();

  dates.forEach((date) => {
    const dayRows = rows.filter((row) => row.date === date);
    const tideValues = dayRows.map((row) => row.tide).filter((value) => value !== null && value !== undefined);
    const lowTide = Math.min(...tideValues);
    const highTide = Math.max(...tideValues);
    const midTide = (lowTide + highTide) / 2;
    const tideRange = (highTide - lowTide) * MID_TIDE_RANGE_RATIO;
    state.tideInfoByDate.set(date, { lowTide, highTide, midTide });

    dayRows.forEach((row) => {
      row.offshoreOk = isOffshore(row, spot);
      row.periodOk = row.wavePeriod !== null && row.wavePeriod >= MIN_WAVE_PERIOD_SECONDS;
      row.midTideOk = row.tide !== null && Math.abs(row.tide - midTide) <= tideRange;
      row.allOk = row.offshoreOk && row.periodOk && row.midTideOk;
      row.level = heightLevel(row);

      const passedCount = [row.offshoreOk, row.periodOk, row.midTideOk].filter(Boolean).length;
      row.quality = row.allOk ? "좋음" : passedCount >= 2 ? "애매" : "나쁨";
      row.reason = !row.offshoreOk ? "바람 불리" : !row.periodOk ? "주기 짧음" : !row.midTideOk ? "조수 애매" : "조건 양호";
    });
  });
}

function average(values) {
  const filtered = values.filter((value) => value !== null && value !== undefined);
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

function segmentScore(segment) {
  const lengthScore = segment.length * 1000;
  const idealPeriodScore = segment.filter((row) => row.wavePeriod >= 7 && row.wavePeriod <= 11).length * 50;
  const windAverage = average(segment.map((row) => row.windSpeed));
  const calmWindScore = Math.max(0, 50 - windAverage);
  const heightFitScore = segment.filter((row) => row.waveHeight <= 2).length * 30;
  return lengthScore + idealPeriodScore + calmWindScore + heightFitScore;
}

function findBestSegment(dayRows) {
  const segments = [];
  let current = [];

  dayRows.forEach((row) => {
    if (row.allOk) {
      current.push(row);
    } else if (current.length) {
      segments.push(current);
      current = [];
    }
  });

  if (current.length) segments.push(current);
  if (!segments.length) return null;
  return segments.sort((a, b) => segmentScore(b) - segmentScore(a))[0];
}

function formatDay(dateKey) {
  const [, month, day] = dateKey.split("-").map(Number);
  return `${month}월 ${day}일`;
}

function formatTime(time) {
  return time.slice(11, 16);
}

function segmentText(segment) {
  const start = formatTime(segment[0].time);
  const last = segment[segment.length - 1].time;
  const [datePart, hourPart] = last.split("T");
  const endHour = String((Number(hourPart.slice(0, 2)) + 1) % 24).padStart(2, "0");
  const end = `${endHour}:00`;
  return `${start} ~ ${end}${end === "00:00" ? ` (${formatDay(addDays(datePart, 1))})` : ""}`;
}

function qualityClass(quality) {
  if (quality === "좋음") return "good";
  if (quality === "애매") return "ok";
  return "bad";
}

function numberText(value, digits) {
  if (value === null || value === undefined || Number.isNaN(value)) return "없음";
  return Number(value).toFixed(digits);
}

function windSpeedText(row, spot) {
  if (row.windSpeed === null || row.windSpeed === undefined) return "없음";
  if (spot.key === "songjeong") {
    return `${row.windSpeed.toFixed(1)}km/h (${(row.windSpeed / 3.6).toFixed(1)}m/s)`;
  }
  return `${row.windSpeed.toFixed(1)}km/h`;
}

function renderStaticSpotText() {
  const spot = activeSpot();
  elements.spotBadge.textContent = spot.badge;
  elements.heroTitle.textContent = spot.title;
  elements.heroCopy.textContent = spot.heroCopy;
  elements.coordinateText.textContent = `${spot.latitude}, ${spot.longitude}`;
  elements.spotDescription.textContent = spot.description;
  elements.ruleSummary.textContent = `${spot.offshoreText} + 7초 이상 + 미드타이드`;
  elements.forecastLabel.textContent = `${spot.shortName} 3일 예보`;
  elements.spotButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.spot === state.activeSpotKey);
  });
}

function render() {
  const dates = [...state.tideInfoByDate.keys()].sort();
  state.bestSegments = dates
    .map((date) => findBestSegment(state.rows.filter((row) => row.date === date)))
    .filter(Boolean);

  elements.dayTabs.innerHTML = "";
  elements.dayPanels.innerHTML = "";

  dates.forEach((date, index) => {
    const dayRows = state.rows.filter((row) => row.date === date);
    const bestSegment = findBestSegment(dayRows);
    const tideInfo = state.tideInfoByDate.get(date);
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = `day-tab${index === 0 ? " is-active" : ""}`;
    tab.textContent = formatDay(date);
    tab.addEventListener("click", () => activateDay(index));
    elements.dayTabs.append(tab);

    const panel = document.createElement("article");
    panel.className = `day-panel${index === 0 ? " is-active" : ""}`;
    panel.innerHTML = buildDayPanelHtml(date, dayRows, bestSegment, tideInfo);
    elements.dayPanels.append(panel);
  });

  renderOverallBest();
}

function buildDayPanelHtml(date, dayRows, bestSegment, tideInfo) {
  const spot = activeSpot();
  const bestHtml = bestSegment
    ? `${segmentText(bestSegment)} <span class="chip good">${heightLevel({ waveHeight: average(bestSegment.map((row) => row.waveHeight)) })}</span>`
    : "세 조건 모두 통과한 시간 없음";

  const tableRows = dayRows
    .map(
      (row) => `
        <tr>
          <td>${formatTime(row.time)}</td>
          <td><span class="chip ${qualityClass(row.quality)}">${row.quality}</span></td>
          <td class="${levelClass(row.level)}">${row.level}</td>
          <td>${numberText(row.waveHeight, 2)}m</td>
          <td>${numberText(row.wavePeriod, 1)}초</td>
          <td>${windDirectionKorean(row.windDirection)}(${Math.round(row.windDirection)}도)</td>
          <td>${windSpeedText(row, spot)}</td>
          <td>${numberText(row.tide, 2)}m</td>
          <td>${row.offshoreOk ? "통과" : "탈락"}</td>
          <td>${row.periodOk ? "통과" : "탈락"}</td>
          <td>${row.midTideOk ? "통과" : "탈락"}</td>
          <td>${row.reason}</td>
        </tr>
      `,
    )
    .join("");

  return `
    <div class="day-card">
      <div class="day-summary">
        <div>
          <span class="label">기준일: ${formatDay(date)} (위치: ${spot.description})</span>
          <strong>${bestHtml}</strong>
        </div>
        <div>
          <span class="label">조수 기준</span>
          <strong>${numberText(tideInfo.lowTide, 2)}m / ${numberText(tideInfo.highTide, 2)}m</strong>
          <small>중간 수위 ${numberText(tideInfo.midTide, 2)}m 근처를 통과 처리</small>
        </div>
        <div>
          <span class="label">주기 해석</span>
          <strong>${bestSegment ? periodDescription(average(bestSegment.map((row) => row.wavePeriod)), spot) : "추천 구간 없음"}</strong>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>시간</th>
              <th>평가</th>
              <th>난이도</th>
              <th>파고</th>
              <th>주기</th>
              <th>풍향</th>
              <th>풍속</th>
              <th>조위</th>
              <th>바람</th>
              <th>주기</th>
              <th>조수</th>
              <th>이유</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;
}

function renderOverallBest() {
  const spot = activeSpot();
  if (!state.bestSegments.length) {
    elements.overallBest.textContent = "추천 시간 없음";
    elements.overallDetail.textContent = "3일 동안 세 조건을 모두 통과한 시간이 없습니다.";
    return;
  }

  const best = state.bestSegments.sort((a, b) => segmentScore(b) - segmentScore(a))[0];
  const date = best[0].date;
  const avgHeight = average(best.map((row) => row.waveHeight));
  const avgPeriod = average(best.map((row) => row.wavePeriod));
  const avgWind = average(best.map((row) => row.windSpeed));

  elements.overallBest.textContent = `${formatDay(date)} ${segmentText(best)}`;
  elements.overallDetail.textContent = `${heightLevel({ waveHeight: avgHeight })} 추천, 평균 파고 ${avgHeight.toFixed(2)}m, 주기 ${avgPeriod.toFixed(1)}초, 풍속 ${avgWind.toFixed(1)}km/h, ${periodDescription(avgPeriod, spot)}`;
}

function activateDay(index) {
  document.querySelectorAll(".day-tab").forEach((tab, tabIndex) => {
    tab.classList.toggle("is-active", tabIndex === index);
  });
  document.querySelectorAll(".day-panel").forEach((panel, panelIndex) => {
    panel.classList.toggle("is-active", panelIndex === index);
  });
}

async function load() {
  const spot = activeSpot();
  elements.loading.hidden = false;
  elements.error.hidden = true;
  elements.refreshButton.disabled = true;
  elements.refreshButton.textContent = "불러오는 중";
  elements.overallBest.textContent = "계산 중";
  elements.overallDetail.textContent = `${spot.shortName} 데이터를 가져오고 있습니다.`;

  try {
    const { startDate, endDate } = getDateRange(spot);
    const { marineJson, windJson } = await fetchForecast(spot, startDate, endDate);
    state.rows = mergeHourlyData(marineJson, windJson);
    judgeRows(state.rows, spot);
    render();
    const updated = new Intl.DateTimeFormat("ko-KR", {
      timeZone: spot.timezone,
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date());
    elements.updatedAt.textContent = `마지막 업데이트: ${spot.shortName} 현지 시간 ${updated}`;
  } catch (error) {
    elements.error.hidden = false;
    elements.error.textContent = `데이터를 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 새로고침해 주세요. (${error.message})`;
  } finally {
    elements.loading.hidden = true;
    elements.refreshButton.disabled = false;
    elements.refreshButton.textContent = "데이터 새로고침";
  }
}

function changeSpot(nextSpotKey) {
  if (!SPOTS[nextSpotKey] || state.activeSpotKey === nextSpotKey) return;
  state.activeSpotKey = nextSpotKey;
  state.rows = [];
  state.bestSegments = [];
  state.tideInfoByDate.clear();
  elements.dayTabs.innerHTML = "";
  elements.dayPanels.innerHTML = "";
  renderStaticSpotText();
  updateClock();
  load();
}

elements.spotButtons.forEach((button) => {
  button.addEventListener("click", () => changeSpot(button.dataset.spot));
});

elements.refreshButton.addEventListener("click", load);
renderStaticSpotText();
updateClock();
setInterval(updateClock, 1000);
load();
