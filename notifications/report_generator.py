"""
Generador de reportes consolidados y bitácora de auditoría en formato Excel (.xlsx) y CSV.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import NotificationResult, AuditNotificationData, DeliveryStatus, ChannelType

logger = logging.getLogger("Notifications.ReportGenerator")


def generate_consolidation_report(
    results: List[NotificationResult],
    audit_data_list: List[AuditNotificationData],
    output_filepath: str
) -> str:
    """
    Genera un informe consolidado en Excel con diseño profesional institucional y trazabilidad completa.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    
    # 1. Crear DataFrame para la Bitácora de Envíos
    # Indexar datos de auditoría por HC
    audit_map = {a.hc_number: a for a in audit_data_list}
    
    rows = []
    for r in results:
        audit_info = audit_map.get(r.hc_number)
        rows.append({
            "ID_Historia_Clinica": r.hc_number,
            "Medico_Evaluado": r.doctor_name,
            "Especialidad": audit_info.specialty if audit_info else "N/A",
            "Canal_Notificacion": r.channel.value,
            "Estado_Envio": r.status.value,
            "Destinatario": r.recipient,
            "Calificacion_Ponderada": f"{audit_info.score:.1f}%" if audit_info else "N/A",
            "Nivel_Riesgo": audit_info.risk_level if audit_info else "N/A",
            "Criterio_Oportunidad_Mejora": audit_info.weak_criterion if audit_info else "N/A",
            "Detalle_Hallazgo_Clinico": audit_info.finding_detail if audit_info else "N/A",
            "ID_Mensaje_Transaccion": r.message_id or "N/A",
            "Fecha_Hora_Procesamiento": r.timestamp,
            "Observaciones_Error": r.error_message or "Sin novedades"
        })
        
    df_bitacora = pd.DataFrame(rows)
    
    # 2. Crear Resumen Ejecutivo
    total_intentos = len(results)
    exitosos = sum(1 for r in results if r.status in (DeliveryStatus.SENT, DeliveryStatus.DRY_RUN_SUCCESS))
    fallidos = sum(1 for r in results if r.status == DeliveryStatus.FAILED)
    omitidos = sum(1 for r in results if r.status == DeliveryStatus.SKIPPED_INVALID_DATA)
    
    email_count = sum(1 for r in results if r.channel == ChannelType.EMAIL)
    wa_count = sum(1 for r in results if r.channel == ChannelType.WHATSAPP)
    
    resumen_data = [
        {"Metrica": "Total Historias Clínicas Auditadas", "Valor": len(audit_data_list)},
        {"Metrica": "Total Notificaciones Procesadas", "Valor": total_intentos},
        {"Metrica": "Notificaciones por Correo Electrónico", "Valor": email_count},
        {"Metrica": "Notificaciones por WhatsApp", "Valor": wa_count},
        {"Metrica": "Envíos Exitosos / Simulados", "Valor": exitosos},
        {"Metrica": "Envíos Omitidos por Datos Inválidos", "Valor": omitidos},
        {"Metrica": "Envíos Fallidos por Error de Red / API", "Valor": fallidos},
        {"Metrica": "Tasa de Efectividad en Entrega", "Valor": f"{(exitosos / total_intentos * 100):.1f}%" if total_intentos > 0 else "0.0%"},
        {"Metrica": "Fecha y Hora de Generación", "Valor": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
    ]
    df_resumen = pd.DataFrame(resumen_data)

    # 3. Guardar con ExcelWriter y aplicar estilizado institucional
    with pd.ExcelWriter(output_filepath, engine="openpyxl") as writer:
        df_bitacora.to_excel(writer, sheet_name="Bitacora_Notificaciones", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen_Ejecutivo", index=False)
        
        # Formato de la hoja Bitácora
        wb = writer.book
        ws_bitacora = writer.sheets["Bitacora_Notificaciones"]
        ws_resumen = writer.sheets["Resumen_Ejecutivo"]
        
        # Paleta de colores
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        
        data_font = Font(name="Segoe UI", size=10)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )
        
        # Estilizar cabecera Bitácora
        for col_idx in range(1, len(df_bitacora.columns) + 1):
            cell = ws_bitacora.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            
        # Estilizar celdas de datos y aplicar badges
        for row_idx in range(2, len(df_bitacora) + 2):
            estado_val = ws_bitacora.cell(row=row_idx, column=5).value
            
            for col_idx in range(1, len(df_bitacora.columns) + 1):
                cell = ws_bitacora.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")
                
                # Colorear estado
                if col_idx == 5:
                    if estado_val in (DeliveryStatus.SENT.value, DeliveryStatus.DRY_RUN_SUCCESS.value):
                        cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                        cell.font = Font(name="Segoe UI", size=10, bold=True, color="166534")
                    elif estado_val == DeliveryStatus.SKIPPED_INVALID_DATA.value:
                        cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                        cell.font = Font(name="Segoe UI", size=10, bold=True, color="92400E")
                    else:
                        cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                        cell.font = Font(name="Segoe UI", size=10, bold=True, color="991B1B")

        # Ajustar ancho de columnas automáticamente
        for col in ws_bitacora.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_bitacora.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        # Estilizar Resumen
        for col_idx in range(1, 3):
            cell = ws_resumen.cell(row=1, column=col_idx)
            cell.fill = PatternFill(start_color="134E4A", end_color="134E4A", fill_type="solid")
            cell.font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            
        for row_idx in range(2, len(df_resumen) + 2):
            for col_idx in range(1, 3):
                cell = ws_resumen.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                if col_idx == 1:
                    cell.font = Font(name="Segoe UI", size=10, bold=True, color="334155")
                    
        ws_resumen.column_dimensions["A"].width = 40
        ws_resumen.column_dimensions["B"].width = 25

    logger.info(f"Reporte consolidado generado exitosamente en: {output_filepath}")
    return output_filepath
