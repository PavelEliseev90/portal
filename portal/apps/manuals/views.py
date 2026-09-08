from hashlib import new
from turtle import title
from django.shortcuts import render
from manuals.models import Manuals, ManualsTag
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
import datetime as DT

'''
def tasks(request):
	try:
		if request.user.is_authenticated:

			tag_id 				= 0
			title 				= ''
			select_activated 	= 0

			manuals = TaskUser.objects.all().order_by('-dateUpdate')
			
			if 'title' in request.GET:
				title = request.GET.get('title')
				manuals = manuals.filter(title__icontains = title) | manuals.filter(text__icontains = title)
			
			if 'select_activated' in request.GET:
				select_activated = int(request.GET.get('select_activated'))
			
			if select_activated == 0:
				manuals = manuals.filter(activated = True)
			elif select_activated == 1:
				manuals = manuals.filter(activated = False)
			
			if request.GET.get('tag_id', ""):
				tag_id = int(request.GET['tag_id'])
				if tag_id > 0:
					manuals = manuals.filter(tags__id = tag_id)
			
			user = request.user
			
			tags = ManualsTag.objects.all()
			
			filtr = {
				'tag_id'			: tag_id,
				'select_activated'	: select_activated,
				'title'				: title
			}
			params = {
				'type'		: 'manuals',
				'user'		: user,
				'manuals'	: manuals,
				'tags'		: tags,
				'filtr'		: filtr
			}
			return render(request, 'manuals/lk_manuals.html', {'params': params})
		else:
			return HttpResponseRedirect('/login')
	except Exception:
		return render(request, 'errors/404.html')
'''

def manuals(request):
	try:
		if request.user.is_authenticated:

			tag_id 				= 0
			title 				= ''
			select_activated 	= 0

			manuals = Manuals.objects.all().order_by('-dateUpdate')
			
			if 'title' in request.GET:
				title = request.GET.get('title')
				manuals = manuals.filter(title__icontains = title) | manuals.filter(text__icontains = title)
			
			if 'select_activated' in request.GET:
				select_activated = int(request.GET.get('select_activated'))
			
			if select_activated == 0:
				manuals = manuals.filter(activated = True)
			elif select_activated == 1:
				manuals = manuals.filter(activated = False)
			
			if request.GET.get('tag_id', ""):
				tag_id = int(request.GET['tag_id'])
				if tag_id > 0:
					manuals = manuals.filter(tags__id = tag_id)
			
			user = request.user
			
			tags = ManualsTag.objects.all().order_by('name')
			manuals = manuals.select_related('author').prefetch_related('tags')
			
			filtr = {
				'tag_id'			: tag_id,
				'select_activated'	: select_activated,
				'title'				: title
			}
			params = {
				'type'		: 'manuals',
				'user'		: user,
				'manuals'	: manuals,
				'tags'		: tags,
				'filtr'		: filtr
			}
			return render(request, 'manuals/lk_manuals.html', {'params': params})
		else:
			return HttpResponseRedirect('/login')
	except Exception:
		return render(request, 'errors/404.html')


def manual_edit(request):
	try:
		if request.user.is_authenticated:
			if request.method == "GET":
				id = 0 
				manual = None
				selected_tag_ids = []
				if 'id' in request.GET:
					id 		= int(request.GET['id'])
					manual 	= Manuals.objects.get(pk=id)
					selected_tag_ids = list(manual.tags.values_list('id', flat=True))
				
				user = request.user
				tags = ManualsTag.objects.all().order_by('name')
				
				params = {
					'type'				: 'manuals',
					'user'				: user,
					'manual'			: manual,
					'tags'				: tags,
					'selected_tag_ids'	: selected_tag_ids,
				}
				return render(request, 'manuals/lk_manual_edit.html', {'params': params})
			else:
				title 		= request.POST['manual_title']
				text 		= request.POST['text']
				activated 	= False
				id_raw		= request.POST.get('uin') or '0'
				try:
					pk = int(id_raw)
				except (TypeError, ValueError):
					pk = 0
				
				if 'activated' in request.POST:
					activated = True
				
				if pk == 0:
					new_manual = Manuals()
					new_manual.dateCreate = DT.datetime.now()
				else:
					new_manual = Manuals.objects.get(pk=pk)

				new_manual.title 		= title
				new_manual.text 		= text
				new_manual.author 		= request.user
				new_manual.dateUpdate 	= DT.datetime.now()
				new_manual.activated 	= activated
				
				new_manual.save()

				new_manual.tags.clear()
				for key in request.POST.keys():
					if key.startswith('tag_id_'):
						tad_id = int(key.replace('tag_id_', ''))
						new_manual.tags.add(ManualsTag.objects.get(id=tad_id))
				
				new_manual.save()

				if new_manual.slug:
					return HttpResponseRedirect('/manuals/' + new_manual.slug + '/')
				return HttpResponseRedirect('/manuals')	
		else:
			return HttpResponseRedirect('/login')
	except Exception:
		return render(request, 'errors/404.html')


def manual(request, pk):
	try:
		if request.user.is_authenticated:
			user 	= request.user
			manual 	= Manuals.objects.get(pk=pk)
			params = {
				'type'		: 'manuals',
				'user'		: user,
				'manual'	: manual
			}
			return render(request, 'manuals/lk_manual.html', {'params': params})
		else:
			return HttpResponseRedirect('/login')
	except Exception:
		return render(request, 'errors/404.html')


def manual_slug(request, slug):
	try:
		if request.user.is_authenticated:
			try:
				user 	= request.user
				manual 	= Manuals.objects.filter(slug = slug)[0]
				params = {
					'type'		: 'manuals',
					'user'		: user,
					'manual'	: manual
				}
				return render(request, 'manuals/lk_manual.html', {'params': params})
			except:
				return render(request, 'errors/404.html')	
		else:
			return HttpResponseRedirect('/login')
	except Exception:
		return render(request, 'errors/404.html')

