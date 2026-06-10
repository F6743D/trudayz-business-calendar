
function getHolidaysUK(year) {
  const h = new Set();
  h.add(`${year}-01-01`);
  h.add(easterFriday(year));
  h.add(easterMonday(year));
  h.add(lastWeekday(year, 5, 1)); // Early May bank holiday
  h.add(nthWeekday(year, 5, 1, 4)); // Spring bank holiday (last Mon May)
  h.add(lastWeekday(year, 8, 1)); // Summer bank holiday
  h.add(`${year}-12-25`);
  h.add(`${year}-12-26`);
  return h;
}

function getHolidaysCA(year) {
  const h = new Set();
  h.add(`${year}-01-01`);
  h.add(easterFriday(year));
  h.add(nthWeekday(year, 5, 1, 3)); // Victoria Day (3rd Mon May... approx)
  h.add(`${year}-07-01`); // Canada Day
  h.add(nthWeekday(year, 8, 1, 1)); // Civic Holiday (1st Mon Aug)
  h.add(nthWeekday(year, 9, 1, 1)); // Labour Day
  h.add(nthWeekday(year, 10, 1, 2)); // Thanksgiving (2nd Mon Oct)
  h.add(`${year}-11-11`); // Remembrance Day
  h.add(`${year}-12-25`);
  h.add(`${year}-12-26`);
  return h;
}

function getHolidaysAU(year) {
  const h = new Set();
  h.add(`${year}-01-01`);
  h.add(`${year}-01-26`); // Australia Day
  h.add(easterFriday(year));
  h.add(easterMonday(year));
  h.add(`${year}-04-25`); // ANZAC Day
  h.add(nthWeekday(year, 6, 1, 2)); // Queen's Birthday (2nd Mon Jun)
  h.add(`${year}-12-25`);
  h.add(`${year}-12-26`);
  return h;
}

function easterFriday(year) {
  const e = easterDate(year);
  e.setDate(e.getDate() - 2);
  return e.toISOString().split('T')[0];
}

function easterMonday(year) {
  const e = easterDate(year);
  e.setDate(e.getDate() + 1);
  return e.toISOString().split('T')[0];
}

function easterDate(year) {
  const a=year%19,b=Math.floor(year/100),c=year%100;
  const d=Math.floor(b/4),e=b%4,f=Math.floor((b+8)/25);
  const g=Math.floor((b-f+1)/3),h=(19*a+b-d-g+15)%30;
  const i=Math.floor(c/4),k=c%4,l=(32+2*e+2*i-h-k)%7;
  const m=Math.floor((a+11*h+22*l)/451);
  const month=Math.floor((h+l-7*m+114)/31);
  const day=((h+l-7*m+114)%31)+1;
  return new Date(year, month-1, day);
}

function getHolidays(year) {
  const h = new Set();
  // New Year's Day
  h.add(`${year}-01-01`);
  // MLK Day (3rd Monday in January)
  h.add(nthWeekday(year, 1, 1, 3));
  // Presidents Day (3rd Monday in February)
  h.add(nthWeekday(year, 2, 1, 3));
  // Memorial Day (last Monday in May)
  h.add(lastWeekday(year, 5, 1));
  // Juneteenth
  h.add(`${year}-06-19`);
  // Independence Day
  h.add(`${year}-07-04`);
  // Labor Day (1st Monday in September)
  h.add(nthWeekday(year, 9, 1, 1));
  // Columbus Day (2nd Monday in October)
  h.add(nthWeekday(year, 10, 1, 2));
  // Veterans Day
  h.add(`${year}-11-11`);
  // Thanksgiving (4th Thursday in November)
  h.add(nthWeekday(year, 11, 4, 4));
  // Christmas
  h.add(`${year}-12-25`);
  return h;
}

function nthWeekday(year, month, dow, n) {
  let d = new Date(year, month-1, 1);
  let count = 0;
  while(true) {
    if(d.getDay() === dow) count++;
    if(count === n) return d.toISOString().split('T')[0];
    d.setDate(d.getDate()+1);
  }
}

function lastWeekday(year, month, dow) {
  let d = new Date(year, month, 0);
  while(d.getDay() !== dow) d.setDate(d.getDate()-1);
  return d.toISOString().split('T')[0];
}

function fmt(d) {
  return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
}

function fmtLong(d) {
  return d.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'});
}

function calculate(businessDays, startDateStr, country) {
  country = country || 'us';
  let current = new Date(startDateStr + 'T12:00:00');
  // skip to first business day
  const _hols0 = country==='uk'?getHolidaysUK(current.getFullYear()):country==='ca'?getHolidaysCA(current.getFullYear()):country==='au'?getHolidaysAU(current.getFullYear()):getHolidays(current.getFullYear());
  while(current.getDay()===0 || current.getDay()===6 || _hols0.has(current.toISOString().split('T')[0])) {
    current.setDate(current.getDate()+1);
  }
  let startDate = new Date(current);
  current.setDate(current.getDate()-1);
  let daysCounted=0, weekendsSkipped=0, holidaysSkipped=0;
  let timeline=[];
  while(daysCounted < businessDays) {
    current.setDate(current.getDate()+1);
    let ds = current.toISOString().split('T')[0];
    let hols = getHolidays(current.getFullYear());
    if(current.getDay()===0||current.getDay()===6){
      weekendsSkipped++;
      timeline.push({date:ds,label:fmt(current),type:'weekend',reason:'Weekend'});
      continue;
    }
    if(hols.has(ds)){
      holidaysSkipped++;
      timeline.push({date:ds,label:fmt(current),type:'holiday',reason:'Bank Holiday'});
      continue;
    }
    daysCounted++;
    let isTarget = daysCounted===businessDays;
    timeline.push({date:ds,label:fmt(current),type:isTarget?'target':'business',reason:`Business Day ${daysCounted}`,day_number:daysCounted});
  }
  let endDate = current;
  let totalCalendarDays = Math.round((endDate-startDate)/(1000*60*60*24));
  return {
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
    end_date_formatted: fmtLong(endDate),
    business_days_requested: businessDays,
    total_calendar_days: totalCalendarDays,
    weekends_skipped: weekendsSkipped,
    holidays_skipped: holidaysSkipped,
    timeline: timeline
  };
}
