from django.shortcuts import render

ASP_VARIANT_TEMPLATES = {
    '1': 'asp/asp.html',
    '2': 'asp/asp_bento.html',
    '3': 'asp/asp_command.html',
    '4': 'asp/asp_22c.html',
}


def asp(request):
    variant = (request.GET.get('v') or '1').strip()
    if variant not in ASP_VARIANT_TEMPLATES:
        variant = '1'
    template = ASP_VARIANT_TEMPLATES[variant]

    params = {
        'type': 'asp',
        'asp_variant': variant,
    }

    return render(request, template, {'params': params})
