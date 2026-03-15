# reports/context_processors.py
# Injects shared data into every template so views don't have to pass it manually.

def global_context(request):
    from reports.models import Committee
    return {
        'committees': Committee.objects.all(),
    }
