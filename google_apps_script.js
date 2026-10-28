/**
 * ==============================================================================
 * FONOCENTER IPS - SCRIPT DE SINCRONIZACIÓN AUTOMÁTICA CON GOOGLE SHEETS
 * Sistema de Auditoría de Calidad en Historias Clínicas
 * Hoja Destino: "Auditoría de Historias Clínicas"
 * ID Hoja de Cálculo: 1-Qcc6LknyrVPubDMMrU37y_6ORlkJLxrPXGOVMpN_DI
 * Normativa: Resolución 1995 de 1999 & Resolución 3100 de 2019
 * ==============================================================================
 * 
 * INSTRUCCIONES DE INSTALACIÓN EN GOOGLE SHEETS:
 * 1. Abre tu hoja de cálculo:
 *    https://docs.google.com/spreadsheets/d/1-Qcc6LknyrVPubDMMrU37y_6ORlkJLxrPXGOVMpN_DI/edit
 * 2. En el menú superior, haz clic en: Extensiones > Apps Script.
 * 3. Borra todo el código existente en el editor y pega este código completo.
 * 4. Haz clic en el botón "Guardar" (ícono de disquete o Ctrl + S).
 * 5. Haz clic en el botón azul superior "Implementar" (Deploy) > "Nueva implementación".
 * 6. En el ícono de engranaje (Tipo), selecciona "Aplicación web" (Web app).
 * 7. Configuración requerida:
 *    - Descripción: Conector Auditoría HC FONOCENTER
 *    - Ejecutar como: "Yo" (tu cuenta de correo de Google)
 *    - Quién tiene acceso: "Cualquier usuario" (Anyone) -> ¡IMPORTANTE para permitir envíos desde la app web!
 * 8. Haz clic en "Implementar", autoriza los permisos que solicite Google.
 * 9. Copia la "URL de la aplicación web" (termina en /exec) y pégala en la aplicación web de Auditoría.
 */

// Configuración de la hoja de cálculo específica
var SPREADSHEET_ID = "1-Qcc6LknyrVPubDMMrU37y_6ORlkJLxrPXGOVMpN_DI";
var TARGET_SHEET_NAME = "Auditoría de Historias Clínicas";

/**
 * Manejador de peticiones POST (Recibe auditorías individuales o en lote)
 */
function doPost(e) {
  try {
    var lock = LockService.getScriptLock();
    lock.waitLock(30000); // Esperar hasta 30 segundos para evitar bloqueos simultáneos
    
    var sheet = getOrCreateTargetSheet();
    var contents = e.postData.contents;
    var data = JSON.parse(contents);
    
    var response = {};
    
    // 1. Caso: Sincronización en lote (Batch sync)
    if (data.action === "batch_sync" && Array.isArray(data.records)) {
      var syncedCount = 0;
      for (var i = 0; i < data.records.length; i++) {
        upsertAuditRecord(sheet, data.records[i]);
        syncedCount++;
      }
      response = {
        status: "success",
        message: "Lote de " + syncedCount + " auditorías sincronizadas exitosamente en 'Auditoría de Historias Clínicas'.",
        count: syncedCount,
        sheetName: sheet.getName(),
        timestamp: new Date().toISOString()
      };
    }
    // 2. Caso: Prueba de conexión
    else if (data.action === "test_connection") {
      response = {
        status: "success",
        message: "Conexión exitosa con la hoja '" + sheet.getName() + "' de FONOCENTER IPS.",
        spreadsheetId: SPREADSHEET_ID,
        sheetName: sheet.getName(),
        timestamp: new Date().toISOString()
      };
    }
    // 3. Caso: Registro individual de auditoría
    else {
      var record = data.record || data;
      upsertAuditRecord(sheet, record);
      response = {
        status: "success",
        message: "Auditoría HC #" + (record.hcNumber || "") + " registrada exitosamente en Google Sheets.",
        recordId: record.id || record.hcNumber,
        sheetName: sheet.getName(),
        timestamp: new Date().toISOString()
      };
    }
    
    lock.releaseLock();
    
    return ContentService
      .createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({
        status: "error",
        message: error.toString(),
        stack: error.stack
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Manejador de peticiones GET (Verificación de estado)
 */
function doGet(e) {
  try {
    var sheet = getOrCreateTargetSheet();
    var data = sheet.getDataRange().getValues();
    
    var result = {
      status: "online",
      institution: "FONOCENTER IPS",
      service: "Conector Google Sheets de Auditoría HC",
      sheetName: sheet.getName(),
      spreadsheetId: SPREADSHEET_ID,
      totalAudits: Math.max(0, data.length - 1),
      timestamp: new Date().toISOString()
    };
    
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Obtiene la hoja "Auditoría de Historias Clínicas" o la crea con la estructura oficial
 */
function getOrCreateTargetSheet() {
  var ss;
  try {
    ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) {
      ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    }
  } catch (e) {
    ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  }
  
  // Buscar coincidencia exacta o por nombres similares
  var sheet = ss.getSheetByName(TARGET_SHEET_NAME);
  if (!sheet) {
    var sheets = ss.getSheets();
    for (var i = 0; i < sheets.length; i++) {
      var name = sheets[i].getName().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      if (name.indexOf("auditoria") !== -1 && name.indexOf("historia") !== -1) {
        sheet = sheets[i];
        break;
      }
    }
  }
  
  // Si no existe, crear la hoja con el nombre exacto
  if (!sheet) {
    sheet = ss.insertSheet(TARGET_SHEET_NAME);
  }
  
  // Verificar si tiene encabezados, de lo contrario crearlos
  if (sheet.getLastRow() === 0 || sheet.getLastColumn() === 0) {
    setupSheetHeaders(sheet);
  } else {
    var firstRow = sheet.getRange(1, 1, 1, Math.min(sheet.getLastColumn(), 5)).getValues()[0];
    if (!firstRow || !firstRow[0] || firstRow[0].toString().trim() === "") {
      setupSheetHeaders(sheet);
    }
  }
  
  return sheet;
}

/**
 * Configura los encabezados estilizados y estructurados según los 17 criterios normativos
 */
function setupSheetHeaders(sheet) {
  var headers = [
    "ID Auditoría",
    "Número HC",
    "Fecha Auditoría",
    "Médico Evaluado",
    "Identificación Paciente",
    "Nombre Paciente",
    "Servicio Asistencial",
    "Calificación (%)",
    "Nivel de Riesgo",
    "Conformidad (>=90%)",
    "C01 - Fecha/Hora/Firma (5%)",
    "C02 - Identificación Completa (5%)",
    "C03 - Valoración Subjetiva (5%)",
    "C04 - Enfermedad Actual (5%)",
    "C05 - Antecedentes y Fármacos (5%)",
    "C06 - Estado Actual Paciente (5%)",
    "C07 - Examen Físico Cefalocaudal (10%)",
    "C08 - Impresión Diagnóstica CIE (5%)",
    "C09 - Adherencia y Educación (5%)",
    "C10 - Conducta y Manejo (5%)",
    "C11 - Justificación Farmacológica (10%)",
    "C12 - Análisis Barthel PAD (5%)",
    "C13 - Análisis FAC PAD (5%)",
    "C14 - Coherencia Registros (5%)",
    "C15 - Evoluciones Clínicas (5%)",
    "C16 - Legibilidad y Redacción (5%)",
    "C17 - Prescripciones y GPC (10%)",
    "Hallazgos y Observaciones",
    "Fecha Sincronización"
  ];
  
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  var headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground("#0F172A"); // Slate 900 oscuro
  headerRange.setFontColor("#2DD4BF"); // Teal 400
  headerRange.setFontWeight("bold");
  headerRange.setFontFamily("Arial");
  headerRange.setFontSize(10);
  headerRange.setHorizontalAlignment("center");
  headerRange.setVerticalAlignment("middle");
  headerRange.setWrap(true);
  
  sheet.setRowHeight(1, 38);
  sheet.setFrozenRows(1);
}

/**
 * Inserta o actualiza un registro de auditoría (Upsert por ID o Número de HC)
 */
function upsertAuditRecord(sheet, record) {
  if (!record) return;
  
  var evals = record.evaluations || record.criteriaScores || {};
  var comments = record.comments || {};
  
  var formatEval = function(val) {
    if (val === undefined || val === null || val === "") return "NO EVALUADO";
    var str = val.toString().toUpperCase();
    if (str === "CUMPLE" || str === "1" || str === "1.0") return "Cumple (100%)";
    if (str === "PARCIAL" || str === "0.5") return "Cumple Parcial (50%)";
    if (str === "NO_CUMPLE" || str === "0" || str === "0.0") return "No Cumple (0%)";
    return val;
  };
  
  // Consolidar comentarios y observaciones
  var commentSummary = [];
  for (var code in comments) {
    if (comments[code] && comments[code].toString().trim() !== "") {
      commentSummary.push("[" + code + "]: " + comments[code].toString().trim());
    }
  }
  var observationsText = commentSummary.length > 0 ? commentSummary.join(" | ") : (record.observations || record.generalObservations || "Sin observaciones registradas.");
  
  var scoreNum = parseFloat(record.score || record.totalScore || 0);
  var riskLevel = record.riskLevel || (scoreNum >= 90 ? "CONFORME" : scoreNum >= 70 ? "MODERADO" : "CRITICO");
  
  var rowData = [
    record.id || ("AUD-" + (record.hcNumber || Date.now().toString().slice(-6))),
    record.hcNumber || "N/A",
    record.auditDate || record.date || Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd"),
    record.doctorName || record.doctor || "No especificado",
    record.patientId || "N/A",
    record.patientName || "No especificado",
    record.serviceType || record.service || "Atención Médica Domiciliaria PAD",
    scoreNum / 100, // Formato decimal para que Google Sheets lo muestre como porcentaje
    riskLevel,
    scoreNum >= 90 ? "SÍ" : "NO",
    formatEval(evals["C01"]),
    formatEval(evals["C02"]),
    formatEval(evals["C03"]),
    formatEval(evals["C04"]),
    formatEval(evals["C05"]),
    formatEval(evals["C06"]),
    formatEval(evals["C07"]),
    formatEval(evals["C08"]),
    formatEval(evals["C09"]),
    formatEval(evals["C10"]),
    formatEval(evals["C11"]),
    formatEval(evals["C12"]),
    formatEval(evals["C13"]),
    formatEval(evals["C14"]),
    formatEval(evals["C15"]),
    formatEval(evals["C16"]),
    formatEval(evals["C17"]),
    observationsText,
    Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss")
  ];
  
  // Buscar si ya existe la auditoría por ID o por (Número HC + Fecha)
  var lastRow = sheet.getLastRow();
  var foundRow = -1;
  var recId = String(rowData[0]).trim();
  var recHc = String(rowData[1]).trim();
  var recDate = String(rowData[2]).trim();
  
  if (lastRow > 1) {
    var idColumn = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
    var hcColumn = sheet.getRange(2, 2, lastRow - 1, 1).getValues();
    var dateColumn = sheet.getRange(2, 3, lastRow - 1, 1).getValues();
    
    for (var r = 0; r < idColumn.length; r++) {
      var curId = String(idColumn[r][0]).trim();
      var curHc = String(hcColumn[r][0]).trim();
      var curDate = String(dateColumn[r][0]).trim();
      
      if ((recId && curId === recId) || (recHc && curHc === recHc && recDate && curDate === recDate)) {
        foundRow = r + 2;
        break;
      }
    }
  }
  
  if (foundRow > 0) {
    sheet.getRange(foundRow, 1, 1, rowData.length).setValues([rowData]);
    formatRowStyling(sheet, foundRow, scoreNum, riskLevel);
  } else {
    sheet.appendRow(rowData);
    var newRow = sheet.getLastRow();
    formatRowStyling(sheet, newRow, scoreNum, riskLevel);
  }
}

/**
 * Aplica estilos, alineación y semaforización a la fila insertada o actualizada
 */
function formatRowStyling(sheet, rowNum, scoreNum, riskLevel) {
  try {
    var range = sheet.getRange(rowNum, 1, 1, 29);
    range.setFontFamily("Arial");
    range.setFontSize(9);
    range.setVerticalAlignment("middle");
    
    // Formato de porcentaje en la columna 8 (Calificación)
    var scoreCell = sheet.getRange(rowNum, 8);
    scoreCell.setNumberFormat("0.0%");
    scoreCell.setHorizontalAlignment("center");
    
    // Formato del nivel de riesgo en la columna 9
    var riskCell = sheet.getRange(rowNum, 9);
    riskCell.setHorizontalAlignment("center");
    
    if (scoreNum >= 90 || riskLevel === "CONFORME") {
      scoreCell.setBackground("#DCFCE7").setFontColor("#15803D").setFontWeight("bold");
      riskCell.setBackground("#DCFCE7").setFontColor("#15803D").setFontWeight("bold");
    } else if (scoreNum >= 70 || riskLevel === "MODERADO") {
      scoreCell.setBackground("#FEF9C3").setFontColor("#A16207").setFontWeight("bold");
      riskCell.setBackground("#FEF9C3").setFontColor("#A16207").setFontWeight("bold");
    } else {
      scoreCell.setBackground("#FEE2E2").setFontColor("#B91C1C").setFontWeight("bold");
      riskCell.setBackground("#FEE2E2").setFontColor("#B91C1C").setFontWeight("bold");
    }
  } catch (e) {
    Logger.log("Error aplicando formato: " + e.message);
  }
}
