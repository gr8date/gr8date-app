# context_processors.py - Legal compliance context processor
from django.conf import settings

def legal_compliance_notice(request):
    """
    Add legal compliance information to template context
    This can be used to display notices to users
    """
    return {
        'LEGAL_COMPLIANCE_MODE': settings.ACTIVITY_LOGGING_ENABLED,
        'MESSAGE_RETENTION_DAYS': settings.MESSAGE_RETENTION_DAYS,
        'DATA_EXPORT_ENABLED': settings.DATA_EXPORT_ENABLED,
        'ADMIN_EMAIL': settings.LEGAL_COMPLIANCE_EMAIL,
    }
