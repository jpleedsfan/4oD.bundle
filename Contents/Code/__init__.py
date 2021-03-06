TITLE = '4oD'
RE_EPISODE_SUMMARY = Regex('<[^<]+?>')
RE_EPISODE_DETAILS = Regex('Series (?P<series>[0-9]+) Episode (?P<episode>[0-9]+)')

BASE_URL = 'http://www.channel4.com'
PROGRAMMES_CATEGORIES = '%s/programmes/tags/4od' % BASE_URL
PROGRAMMES_FEATURED = '%s/programmes/4od' % BASE_URL
PROGRAMMES_BY_DATE = '%s/programmes/4od/episode-list/date/%%s' % BASE_URL
PROGRAMMES_BY_CATEGORY = '%s/programmes/tags/%%s/4od/title/page-%%%%d' % BASE_URL
PROGRAMMES_BY_LETTER = '%s/programmes/atoz/%%s/4od/page-%%%%d' % BASE_URL
PROGRAMMES_SEARCH = '%s/programmes/long-form-search/?q=%%s' % BASE_URL

###################################################################################################
def Start():

	ObjectContainer.title1 = TITLE
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:22.0) Gecko/20100101 Firefox/22.0'

###################################################################################################
@handler('/video/4od', TITLE)
def MainMenu():

	oc = ObjectContainer(no_cache=True)

	if not Platform.HasWebKit:
		oc.header = 'Not supported'
		oc.message = 'Server platform not supported'
		return oc
	elif not Platform.HasFlash:
		oc.header = 'Missing Flash plugin'
		oc.message = 'Flash browser plugin is missing'
		return oc

	if Prefs['email'] and Prefs['password']:
		oc.add(DirectoryObject(key=Callback(BrowseDate, title='Browse by Date'), title='Browse by Date'))
		oc.add(DirectoryObject(key=Callback(BrowseCategory, title='Browse by Category'), title='Browse by Category'))
		oc.add(DirectoryObject(key=Callback(BrowseAlphabetically, title='Browse Alphabetically'), title='Browse Alphabetically'))
		oc.add(DirectoryObject(key=Callback(FeaturedCategory, title='Featured'), title='Featured'))
		oc.add(InputDirectoryObject(key=Callback(Search), title='Search', prompt='Search for Programmes'))

	oc.add(PrefsObject(title='Preferences'))

	return oc

####################################################################################################
@route('/video/4od/browsebydate')
def BrowseDate(title):

	oc = ObjectContainer(title2=title)

	for i in range(30):
		date = Datetime.Now() - Datetime.Delta(days = i)
		date_key = date.strftime('%Y/%m/%d')
		date_label = date.strftime('%A %d %B')

		oc.add(DirectoryObject(
			key = Callback(Schedule, title=date_label, date=date_key),
			title = date_label
		))

	return oc

####################################################################################################
@route('/video/4od/browsebydate/schedule')
def Schedule(title, date):

	oc = ObjectContainer(title2=title)
	programmes = HTML.ElementFromURL(PROGRAMMES_BY_DATE % date, cacheTime=1800).xpath('//li')

	for p in programmes:
		title = p.xpath('.//a/span/text()')[0].strip()
		time = p.xpath('.//span[@class="txTime"]')[0].text.strip()
		channel = p.xpath('.//span[@class="txChannel"]')[0].text.strip()
		url = p.xpath('.//a')[0].get('href').replace('4od#', '4od/player/')
		thumb = p.xpath('.//a/img')[0].get('src').rsplit('_',1)[0] + '_625x352.jpg'

		if url.find(BASE_URL) == -1:
			url = BASE_URL + url
		if thumb.find(BASE_URL) == -1:
			thumb = BASE_URL + thumb

		oc.add(EpisodeObject(
			url = url,
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb)
		))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
@route('/video/4od/browsebycategory')
def BrowseCategory(title):

	oc = ObjectContainer(title2=title)
	titles = []
	categories = HTML.ElementFromURL(PROGRAMMES_CATEGORIES, cacheTime=CACHE_1DAY).xpath('//div[contains(@class,"category-nav")]//li/a')

	for c in categories:
		title = c.text.strip()

		if title not in titles:
			titles.append(title)
			tag = c.get('href').split('/')[3]

			oc.add(DirectoryObject(
				key = Callback(Programmes, title=title, tag=tag),
				title = title
			))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		oc.objects.sort(key=lambda obj: obj.title)
		return oc

####################################################################################################
@route('/video/4od/browsealphabetically')
def BrowseAlphabetically(title):

	oc = ObjectContainer(title2=title)

	# A to Z
	for char in list(String.UPPERCASE):
		oc.add(DirectoryObject(
			key = Callback(Programmes, title=char, char=char),
			title = char
		))

	# 0-9
	oc.add(DirectoryObject(
		key = Callback(Programmes, title='0-9', char='0-9'),
		title = '0-9'
	))

	return oc

####################################################################################################
@route('/video/4od/programmes')
def Programmes(title, tag=None, char=None):

	oc = ObjectContainer(title2=title)

	if tag != None:
		content_url = PROGRAMMES_BY_CATEGORY % tag
	elif char != None:
		content_url = PROGRAMMES_BY_LETTER % char.lower()

	programmes = GetProgrammes(content_url)

	for p in programmes:
		thumb = p['thumb']

		if thumb.find(BASE_URL) == -1:
			thumb = BASE_URL + thumb

		oc.add(DirectoryObject(
			key = Callback(Series, title=p['title'], url=p['url'], thumb=thumb),
			title = p['title'],
			thumb = Resource.ContentsOfURLWithFallback(url=thumb)
		))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
def GetProgrammes(url, page=1):

	result = []

	try:
		programmes = HTML.ElementFromURL(url % page, cacheTime=CACHE_1DAY).xpath('//div[contains(@class,"programmes")]//li')

		for p in programmes:
			prog = {}
			prog['title'] = p.xpath('./h3/a/span')[0].text.strip()
			prog['summary'] = p.xpath('./p[@class="synopsis"]/text()[1]')[0].strip()
			prog['url'] = p.xpath('./h3/a')[0].get('href') + '/4od'
			prog['thumb'] = p.xpath('./h3/a/img')[0].get('src').rsplit('_',1)[0] + '_625x352.jpg'
			result.append(prog)

		# More pages?
		next_page = HTML.ElementFromURL(url % page, cacheTime=CACHE_1DAY).xpath('//*[contains(@class,"nextUrl") and not(contains(@class,"endofresults"))]')

		if len(next_page) > 0:
			result.extend(GetProgrammes(url, page=page+1))
	except:
		pass

	return result

####################################################################################################
@route('/video/4od/series')
def Series(title, url, thumb=None):

	oc = ObjectContainer(title2=title)

	if url.find(BASE_URL) == -1:
		url = BASE_URL + url

	if thumb != None:
		if thumb.find(BASE_URL) == -1:
			thumb = BASE_URL + thumb
	else:
		thumb = GetThumb(series_page=url)

	series = HTML.ElementFromURL(url, cacheTime=CACHE_1DAY).xpath('//div[contains(@class,"seriesLink")]//li/a')

	for s in series:
		title = s.text.strip()

		if len(title) <= 2 and len(title) > 0:
			title = 'Series ' + title

		id = s.get('href').strip('#')

		oc.add(DirectoryObject(
			key = Callback(Episodes, title=title, url=url, id=id, series_thumb=thumb),
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb)
		))

	if len(oc) < 1:
		return ObjectContainer(heaer='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
@route('/video/4od/episodes')
def Episodes(title, url, id, series_thumb=None):

	oc = ObjectContainer(title2=title)
	page = HTML.ElementFromURL(url)
	show = page.xpath('//h1[@class = "brandTitle"]')[0].get('alt')
	episodes = page.xpath('//li[@id="' + id + '"]/ol/li')

	for e in episodes:
		title = e.get('data-episodetitle')
		summary = RE_EPISODE_SUMMARY.sub('', e.get('data-episodesynopsis'))

		try:
			episode_details_dict = RE_EPISODE_DETAILS.match(e.get('data-episodeinfo')).groupdict()
			series = int(episode_details_dict['series'])
			episode = int(episode_details_dict['episode'])
		except:
			series = None
			episode = None

		try:
			date = Datetime.ParseDate(e.get('data-txdate'))
		except:
			date = None

		thumb = e.get('data-image-url').rsplit('_',1)[0] + '_625x352.jpg'
		if len(thumb) != 0 and thumb.find(BASE_URL) == -1:
			thumb = BASE_URL + thumb

		thumb_urls = [thumb]
		if series_thumb:
			thumb_urls.append(series_thumb)

		episode_url = url + '/player/' + e.get('data-assetid')
		if episode_url.find(BASE_URL) == -1:
			episode_url = BASE_URL + episode_url

		oc.add(EpisodeObject(
			url = episode_url,
			show = show,
			title = title,
			summary = summary,
			season = series,
			index = episode,
			originally_available_at = date,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb_urls)
		))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
@route('/video/4od/featuredcategory')
def FeaturedCategory(title):

	oc = ObjectContainer(title2=title)
	i = 0
	categories = HTML.ElementFromURL(PROGRAMMES_FEATURED).xpath('//li[@class="fourOnDemandCollection"]')

	for c in categories:
		title = c.xpath('./h2')[0].text.strip()
		i = i + 1

		if title == 'FILM4oD':
			continue
		else:
			title = title.title().replace("'S", "'s")

		oc.add(DirectoryObject(
			key = Callback(Featured, title=title, i=i),
			title = title
		))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
@route('/video/4od/featured', i=int)
def Featured(title, i):

	oc = ObjectContainer(title2=title)
	programmes = HTML.ElementFromURL(PROGRAMMES_FEATURED).xpath('//li[@class="fourOnDemandCollection"][' + str(i) + ']//li')

	for p in programmes:
		details = JSON.ObjectFromString(p.get('data-metadata'))
		if details['url'].find('/4od') == -1:
			continue

		title = details['title']
		if details.has_key('title2'):
			title = details['title2']

		summary = details['synopsis']

		thumb = details['img']['src']
		if thumb.find(BASE_URL) == -1:
			thumb = BASE_URL + thumb

		oc.add(DirectoryObject(
			key = Callback(Series, title=title, url=details['url'], thumb=thumb),
			title = title,
			summary = summary,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb)
		))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message='This directory is empty')
	else:
		return oc

####################################################################################################
# Default search query for automated tester
def Search(query='grand designs'):

	oc = ObjectContainer(title2='Search: ' + query)
	result = JSON.ObjectFromURL(PROGRAMMES_SEARCH % (String.Quote(query, usePlus=True)))

	if len(result) > 0:
		for r in result['results']:
			title = r['value'].strip()
			url = r['siteUrl']

			oc.add(DirectoryObject(
				key = Callback(Series, title=title, url=url),
				title = title,
				thumb = Callback(GetThumbCallback, series_page=url)
			))

	if len(oc) < 1:
		return ObjectContainer(header='No results', message='Your search didn\'t return any results.')
	else:
		return oc

####################################################################################################
def GetThumb(series_page):

	thumb_url = ''

	try:
		if series_page != None:

			if series_page.find(BASE_URL) == -1:
				series_page = BASE_URL + series_page

			if series_page.find('/4od') > 0:
				series_page = series_page[0:-4]

			thumb_url = HTML.ElementFromURL(series_page).xpath('//img[@id="heroImage"]')[0].get('src')
			if thumb_url.find(BASE_URL) == -1:
				thumb_url = BASE_URL + thumb_url
	except:
		pass

	return thumb_url

####################################################################################################
def GetThumbCallback(series_page):

	return Redirect(GetThumb(series_page=series_page))
