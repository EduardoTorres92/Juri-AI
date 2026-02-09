from django.contrib.auth.decorators import login_required
from django.contrib.messages import constants
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse

from .models import AreaAtuacao, DocumentoArea


@login_required
def areas_list(request):
    if request.method == 'GET':
        from django.db.models import Q
        from django.core.paginator import Paginator

        qs = AreaAtuacao.objects.filter(user=request.user).order_by('nome')

        busca = (request.GET.get('q') or '').strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))

        total = qs.count()
        per_page = 10
        paginator = Paginator(qs, per_page)
        page_num = request.GET.get('page', 1)
        page = paginator.get_page(page_num)
        areas_list_data = list(page.object_list)

        doc_por_area = {}
        for d in DocumentoArea.objects.filter(area__in=areas_list_data).order_by('area', '-data_upload'):
            if d.area_id not in doc_por_area:
                doc_por_area[d.area_id] = (d.nome_exibicao, d.data_upload)

        areas_com_ultimo = []
        for a in areas_list_data:
            doc = doc_por_area.get(a.id)
            if doc:
                ultimo_desc, ultimo_data = doc[0], doc[1]
            else:
                ultimo_desc, ultimo_data = None, None
            areas_com_ultimo.append({
                'area': a,
                'ultimo_desc': ultimo_desc,
                'ultimo_data': ultimo_data,
            })

        return render(request, 'areas/areas.html', {
            'areas_com_ultimo': areas_com_ultimo,
            'page': page,
            'paginator': paginator,
            'total': total,
            'busca': busca,
        })
    elif request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        descricao = (request.POST.get('descricao') or '').strip()
        if not nome:
            messages.add_message(request, constants.ERROR, 'Nome é obrigatório.')
            return redirect('areas_list')
        AreaAtuacao.objects.create(
            nome=nome,
            descricao=descricao,
            user=request.user,
        )
        messages.add_message(request, constants.SUCCESS, 'Área de atuação criada com sucesso!')
        return redirect('areas_list')


@login_required
def area_detail(request, id):
    area = get_object_or_404(AreaAtuacao, id=id, user=request.user)
    if request.method == 'GET':
        documentos = DocumentoArea.objects.filter(area=area)
        documento_processando = request.GET.get('documento_processando')
        return render(request, 'areas/area.html', {
            'area': area,
            'documentos': documentos,
            'documento_processando': documento_processando,
        })
    elif request.method == 'POST':
        tipo = request.POST.get('tipo', 'OUTRO')
        documento = request.FILES.get('documento')
        nome = (request.POST.get('nome') or '').strip()
        data = request.POST.get('data')

        if not documento:
            messages.add_message(request, constants.ERROR, 'Selecione um arquivo.')
            return redirect('area_detail', id=area.id)

        doc = DocumentoArea(area=area, tipo=tipo, arquivo=documento, nome=nome)
        if data:
            data_upload = parse_datetime(data)
            if data_upload:
                doc.data_upload = data_upload
        doc.save()

        messages.add_message(
            request, constants.SUCCESS,
            'Documento enviado com sucesso! O processamento (OCR e indexação) está em andamento em segundo plano.'
        )
        url = reverse('area_detail', kwargs={'id': area.id})
        return redirect(f'{url}?documento_processando={doc.id}')


@login_required
def area_editar(request, id):
    area = get_object_or_404(AreaAtuacao, id=id, user=request.user)
    if request.method == 'GET':
        return render(request, 'areas/area_editar.html', {'area': area})
    elif request.method == 'POST':
        area.nome = request.POST.get('nome', '').strip()
        area.descricao = (request.POST.get('descricao') or '').strip()
        area.save()
        messages.add_message(request, constants.SUCCESS, 'Área atualizada com sucesso!')
        return redirect('area_detail', id=area.id)


@login_required
def documento_area_excluir(request, id):
    documento = get_object_or_404(DocumentoArea, id=id)
    if documento.area.user_id != request.user.id:
        messages.add_message(request, constants.ERROR, 'Acesso negado.')
        return redirect('areas_list')
    area_id = documento.area_id
    documento.arquivo.delete(save=False)
    documento.delete()
    messages.add_message(request, constants.SUCCESS, 'Documento excluído com sucesso.')
    return redirect('area_detail', id=area_id)


@login_required
def documento_area_renomear(request, id):
    documento = get_object_or_404(DocumentoArea, id=id)
    if documento.area.user_id != request.user.id:
        messages.add_message(request, constants.ERROR, 'Acesso negado.')
        return redirect('areas_list')
    if request.method == 'POST':
        nome = (request.POST.get('nome') or '').strip()
        if nome:
            documento.nome = nome
            documento.save()
            messages.add_message(request, constants.SUCCESS, 'Documento renomeado com sucesso.')
        return redirect('area_detail', id=documento.area_id)
    return redirect('area_detail', id=documento.area_id)


@login_required
def documento_area_status(request, id):
    """Retorna se o documento da área já foi processado (OCR concluído)."""
    documento = get_object_or_404(DocumentoArea, id=id)
    if documento.area.user_id != request.user.id:
        return JsonResponse({'processado': False, 'erro': 'Acesso negado'}, status=403)
    processado = bool(documento.content and str(documento.content).strip())
    return JsonResponse({'processado': processado})
