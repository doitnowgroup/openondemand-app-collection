// Variable global para almacenar la lista completa de módulos
let allModules = [];
let moduleListContainer;  // Referencia global al contenedor de módulos
const selectedModulesSet = new Set(); // ✅ Para mantener persistente la selección

// Esperar a que el documento esté listo
$(document).ready(function () {

  $('#batch_connect_session_context_selected_modules').val('');
  $('#batch_connect_session_context_module_filter').val('');

  // Atar evento input al filtro de módulos
  $('#batch_connect_session_context_module_filter').on('input', function () {
    updateFilteredModules(); // Llama a la función cuando el usuario escribe
  });

  // Seleccionar el input generado por module_list
  const moduleListInput = $('#module_list_container');

  if (moduleListInput.length > 0) {
    moduleListContainer = createModuleListContainer();
    moduleListInput.replaceWith(moduleListContainer);

    // Cargar módulos
    $.ajax({
      url: 'https://10.3.3.65:5000/modules',
      type: 'GET',
      success: function (response) {
        if (response.success && response.modules && response.modules.length > 0) {
          allModules = response.modules;
          renderModuleList(allModules); // Mostrar todo al inicio
        }
      }
    });

    // Evento change
    $(document).on('change', 'input[name="modules"]', function () {
      const moduleName = $(this).val();
      if ($(this).is(':checked')) {
        selectedModulesSet.add(moduleName);
      } else {
        selectedModulesSet.delete(moduleName);
      }

      // Actualizar campo oculto
      $('#batch_connect_session_context_selected_modules').val(Array.from(selectedModulesSet).join(' '));
    });
  }
});

// Renderizado de módulos respetando selección previa
function renderModuleList(modules) {
  moduleListContainer.empty();

  modules.forEach((module) => {
    const isChecked = selectedModulesSet.has(module) ? 'checked' : '';
    const moduleElement = `
      <div>
        <input type="checkbox" id="module_${module}" name="modules" value="${module}" ${isChecked}>
        <label for="module_${module}">${module}</label>
      </div>
    `;
    moduleListContainer.append(moduleElement);
  });
}

// Filtro dinámico
function updateFilteredModules() {
  const filterText = $('#batch_connect_session_context_module_filter').val().toLowerCase().trim();

  if (filterText === '') {
    renderModuleList(allModules); // Mostrar todo si está vacío
  } else {
    const filteredModules = allModules.filter((module) =>
      module.toLowerCase().includes(filterText)
    );
    renderModuleList(filteredModules);
  }
}

// Crear contenedor
function createModuleListContainer() {
  return $('<div>', {
    id: 'module_list_container',
    style: `
      background: none;
      border: 1px solid #ccc;
      padding: 10px;
      margin-top: 1em;
      margin-bottom: 16px;
      height: 200px;
      overflow-y: auto;
    `,
  });
}

