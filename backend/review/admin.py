from django.contrib import admin

from .models import (
    Airport,
    AuditEvent,
    EmissionFactor,
    Facility,
    IngestionBatch,
    NormalizedActivity,
    Organization,
    PlantLookup,
    RawRecord,
    ReviewFlag,
    SourceSystem,
    UnitConversion,
)


admin.site.register(Organization)
admin.site.register(Facility)
admin.site.register(SourceSystem)
admin.site.register(PlantLookup)
admin.site.register(Airport)
admin.site.register(UnitConversion)
admin.site.register(EmissionFactor)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)
admin.site.register(NormalizedActivity)
admin.site.register(ReviewFlag)
admin.site.register(AuditEvent)

