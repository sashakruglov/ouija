
import calendar
from collections import Counter
from contextlib import closing
from datetime import timedelta
from itertools import groupby

from flask import g, jsonify, request, render_template, url_for

from app import app
from app.forms import DatepickerForm


class CSetSummary(object):
    def __init__(self, cset_id):
        self.cset_id = cset_id
        self.green = Counter()
        self.orange = Counter()
        self.red = Counter()
        self.blue = Counter()


def no_content():
    return jsonify({'error': 'No data found for your request.'})


def get_date_range(dates):
    if dates:
        return {'start_date': min(dates).strftime('%Y-%m-%d %H:%M'),
                'end_date': max(dates).strftime('%Y-%m-%d %H:%M')}


def get_jobs_limit(start_date, end_date):
    days_to_show = (end_date - start_date).days
    jobs_per_day = app.config['JOB_PER_DAY_LIMIT']

    if days_to_show <= 8:
        jobs_limit = 5
    else:
        jobs_limit = int(round(days_to_show * jobs_per_day))
    return jobs_limit


def calculate_fail_rate(passes, retries, totals):
    if passes == totals:
        results = (0, 0)
    else:
        results = []
        for denominator in [totals - retries, totals]:
            try:
                result = 100 - (passes * 100) / float(denominator)
            except ZeroDivisionError:
                result = 0
            results.append(round(result, 1))
    return dict(zip(('fail_rate', 'fail_rate_retries'), results))


@app.route('/')
def index():
    return render_template('index.html', page_title='Home')


@app.route('/platform/<platform>')
def android_failures(platform):
    context = {
        'page_title': '%s failure rate' % platform.capitalize(),
        'form': DatepickerForm(request.args),
        'api_url': url_for('get_platform_data', platform=platform)}
    return render_template('platforms.html', **context)


@app.route('/slaves')
def slave_failures():
    context = {
        'page_title': 'Slave failures',
        'form': DatepickerForm(request.args)}
    return render_template('slaves.html', **context)


@app.route('/results_day_flot')
def test_results_day_flot():
    context = {
        'page_title': 'Test results time series',
        'form': DatepickerForm(request.args),
        'platforms': app.config['DAY_FLOT_PLATFORMS']}
    return render_template('results_day_flot.html', **context)


@app.route('/wiki')
def wiki_update():
    context = {
        'platforms': ('android2.3', 'android4.0')}
    return render_template('wiki_update.html', **context)


@app.route('/api/platform/<platform>')
def get_platform_data(platform):
    form = DatepickerForm(request.args)

    if form.validate():
        start_date = form.start_date.data
        end_date = form.end_date.data + timedelta(days=1)
    else:
        return jsonify(error=form.errors)

    with closing(g.db.cursor()) as cursor:
        cursor.execute("""SELECT DISTINCT (revision) FROM testjobs
                          WHERE platform=%s AND branch="mozilla-central"
                          AND date BETWEEN %s AND %s
                          ORDER BY date DESC;""",
                          (platform, start_date, end_date))

        csets = cursor.fetchall()
        if not csets:
            return no_content()

        cset_summaries = []
        test_summaries = {}
        dates = []

        summary = dict().fromkeys(
            'green orange blue red'.split(), 0)

        for cset in csets:
            cset_id = cset[0]
            cset_summary = CSetSummary(cset_id)

            cursor.execute("""SELECT result, testtype, date FROM testjobs
                              WHERE platform=%s AND buildtype="opt" and revision=%s
                              ORDER BY testtype""", (platform, cset_id))
            test_results = cursor.fetchall()

            for res, testtype, date in test_results:
                test_summary = test_summaries.setdefault(testtype, summary.copy())
                if res == 'success':
                    cset_summary.green[testtype] += 1
                    test_summary['green'] += 1
                elif res == 'testfailed':
                    cset_summary.orange[testtype] += 1
                    test_summary['orange'] += 1
                elif res == 'retry':
                    cset_summary.blue[testtype] += 1
                    test_summary['blue'] += 1
                elif res == 'exception' or res == 'busted':
                    cset_summary.red[testtype] += 1
                    test_summary['red'] += 1
                elif res == 'usercancel':
                    app.logger.debug('usercancel')
                else:
                    app.logger.warning('UNRECOGNIZED RESULT: %s' % res)
                dates.append(date)
            cset_summaries.append(cset_summary)

    # sort tests alphabetically and append total & percentage to end of the list
    test_types = sorted(test_summaries.keys()) + ['total', 'percentage']

    # calculate total stats and percentage
    total = Counter()
    for test in test_summaries.values():
        total.update(test)
    test_count = sum(total.values())

    percentage = {}
    for key in total:
        percentage[key] = round((100.0 * total[key] / test_count), 2)

    test_summaries['total'] = total
    test_summaries['percentage'] = percentage

    fail_rates = calculate_fail_rate(passes=total['green'],
                                     retries=total['blue'],
                                     totals=test_count)

    return jsonify(test_types=test_types,
                   by_revision=cset_summaries,
                   by_test=test_summaries,
                   fail_rates=fail_rates,
                   dates=get_date_range(dates))


@app.route('/api/slaves/')
def get_slaves_data():
    form = DatepickerForm(request.args)

    if form.validate():
        start_date = form.start_date.data
        end_date = form.end_date.data + timedelta(days=1)
    else:
        return jsonify(error=form.errors)

    with closing(g.db.cursor()) as cursor:
        cursor.execute("""SELECT slave, result, date FROM testjobs
                          WHERE result IN ("retry", "testfailed", "success", "busted", "exception")
                          AND date BETWEEN %s AND %s
                          ORDER BY date;""", (start_date, end_date))
        query_results = cursor.fetchall()

    if not query_results:
        return no_content()

    dates = set()
    data = {}
    summary = dict.fromkeys(
        'fail retry infra success total since_last_success'.split(),
         0)

    for name, result, date in query_results:
        data.setdefault(name, summary.copy())
        data[name]['since_last_success'] += 1
        if result == 'testfailed':
            data[name]['fail'] += 1
        elif result == 'retry':
            data[name]['retry'] += 1
        elif result == 'success':
            data[name]['success'] += 1
            data[name]['since_last_success'] = 0
        elif result == 'busted' or result == 'exception':
            data[name]['infra'] += 1
        data[name]['total'] += 1
        dates.add(date)

    # filter slaves
    jobs_limit = get_jobs_limit(start_date, end_date)
    filetered_slaves = set([slave for slave in data if data[slave]['total'] > jobs_limit])
    if not filetered_slaves:
        return no_content()

    # calculate failure rate only for slaves that we're going to display
    for slave in filetered_slaves:
        results = data[slave]
        fail_rates = calculate_fail_rate(results['success'],
                                         results['retry'],
                                         results['total'])
        data[slave]['sfr'] = fail_rates

    # group slaves by platform and calculate platform failure rate
    platforms = {}
    slaves = sorted(data.keys())

    for platform, slave_group in groupby(slaves, lambda x: x.rsplit('-', 1)[0]):
        slaves = list(slave_group)

        # don't calculate failure rate for platform we're not going to show
        if not any(slave in filetered_slaves for slave in slaves):
            continue

        platforms[platform] = {}
        results = {}

        for label in ('success', 'retry', 'total'):
            results[label] = sum([data[slave][label] for slave in slaves])

        fail_rates = calculate_fail_rate(results['success'],
                                         results['retry'],
                                         results['total'])
        platforms[platform].update(fail_rates)

    # remove data that we don't need
    for slave in data.keys():
        if slave not in filetered_slaves:
            del data[slave]

    return jsonify(slaves=data,
                   platforms=platforms,
                   dates=get_date_range(dates),
                   jobs_limit=jobs_limit)


@app.route('/api/flot/')
def get_day_flot_data():
    """Returns the total failures/total jobs data per day for all platforms.

    It is sending the data in the format required by flot.
    Flot is a jQuery package used for 'attractive' plotting
    """
    form = DatepickerForm(request.args)

    if form.validate():
        start_date = form.start_date.data
        end_date = form.end_date.data + timedelta(days=1)
    else:
        return jsonify(error=form.errors)

    data_platforms = {}
    with closing(g.db.cursor()) as cursor:
        for platform in app.config['DAY_FLOT_PLATFORMS'].values():
            cursor.execute("""SELECT DATE(date) as day,
                                     SUM(result="testfailed"),
                                     COUNT(*)
                              FROM testjobs
                              WHERE platform=%s AND
                                    date BETWEEN %s AND %s
                              GROUP BY day;""", (platform, start_date, end_date))

            query_results = cursor.fetchall()
            if not query_results:
                return no_content()

            dates = set()
            data = {'failures': [], 'totals': []}

            for day, fail, total in query_results:
                dates.add(day)
                timestamp = calendar.timegm(day.timetuple()) * 1000
                data['failures'].append((timestamp, int(fail)))
                data['totals'].append((timestamp, int(total)))

            data_platforms[platform] = {'data': data, 'dates': get_date_range(dates)}

    return jsonify(data_platforms)
