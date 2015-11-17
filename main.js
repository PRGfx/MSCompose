'use strict';
var project_config = null;
var current_build_target = '';
var save_buildconfig = function() {
	$.post('save_config?path=' + current_project.path, JSON.stringify(project_config), function(){
		console.info('saved config');
	});
};
var changed_sourceFiles = function() {
	project_config[current_build_target].files = $('#sourcefileList').dragswap('toArray');
	save_buildconfig();
};
var treeview = (function(){
	var reload = function(path){
		$('#treeview').html('');
		$.get('/list_files?path=' + path, function(data){
			buildTree(data);
			highlight();
			filter($('#treefilter').val());
		});
	};

	var buildTree = function(data) {
		var counter = 0;
		var buildSubtree = function(data, parent, level, path) {
			var list = $('<ul>').appendTo(parent);
			var buildCallback = function(element) {
				return function(){
					var file = $(element).val();
					if ($(element).is(':checked')) {
						var parts = file.split('/'), filename = parts.pop(-1), path = parts.join('/') + '/';
						$('<li class=\'noselect\'>').html('<span class=\'path\'>'+path+'</span>'+filename).attr('id', file).appendTo('#sourcefileList');
					} else {
						$('#sourcefileList').find('li').each(function(i, el) {
							if ($(el).attr('id') == file) $(el).remove();
						});
					}
					changed_sourceFiles();
				};
			};
			for(var i = 0; i < data.length; i++) {
				var item = $('<li>').appendTo(list);
				var itemId = 'item' + (++counter);
				var checkbox = $('<input type=\'checkbox\' id=\'' + itemId + '\'>').appendTo(item);
				$('<label for=\'' + itemId + '\'>').text(data[i].name).appendTo(item);
				if (data[i].type == 'directory') {
					$(item).addClass('directory');
					var subpath = level > 1 ? path + data[i].name + '/' : '';
					item.append(buildSubtree(data[i].children, list, level + 1, subpath));
					if (level >= 3)
						checkbox.attr('checked', 'checked');
				} else {
					checkbox.addClass('file').attr('value', path + data[i].name);
					checkbox.on('change', function(){
						var file = $(this).val();
						if ($(this).is(':checked')) {
							var parts = file.split('/'), filename = parts.pop(-1), path = parts.join('/') + '/';
							$('<li class=\'noselect\'>').html('<span class=\'path\'>'+path+'</span>'+filename).attr('id', file).appendTo('#sourcefileList');
						} else {
							$('#sourcefileList').find('li').each(function(i, el) {
								if ($(el).attr('id') == file) $(el).remove();
							});
						}
						changed_sourceFiles();
					});
				}
			}
			return list;
		};
		buildSubtree(data, $('#treeview'), 1, '');
	};

	var filter = function(expression) {
		var regexstr = expression.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, '\\$&');
		regexstr = regexstr.replace('*', '.*?');
		var re = new RegExp(regexstr, 'i');
		$('#treeview').find('li').each(function(i, e){
			if (re.test($(e).text())) $(e).show();
			else $(e).hide();
		});
	};

	var highlight = function() {
		var checked = function(){ return this.checked && !$(this).parent().hasClass('directory'); };
		$('#treeview').find('input').filter(checked).prop('checked', false);
		$('#treeview').find('input').each(function(i,j){
			if (project_config[current_build_target].files.indexOf($(j).val()) >= 0)
				$(j).prop('checked', true);
		});
	};

	return {
		reload: reload,
		filter: filter,
		highlight_files: highlight
	};
}).call();

var reload_tree = treeview.reload;
function setupFilter() {
	$('#treefilter').keyup(function(){
		treeview.filter($(this).val());
	});
}

var projects = [];
var current_project = null;
var current_project_index = -1;
function reload_projectlist() {
	projects.sort(function(b, a){return (a.name < b.name) ? 1 : ((b.name < a.name) ? -1 : 0);});
	$('#project_list').html('');
	for (var i = 0; i < projects.length; i++) {
		var project = projects[i];
		$('<div class="project" onclick="load_project(this, '+i+')">\
			<h2>' + project.name + '</h2><span class="path">' + project.path + '</span>\
			<div class="actions"><span onclick="edit_project(' + i + ')" class="fa fa-pencil" title="Edit"></span>\
			<span onclick="remove_project(' + i + ')" class="fa fa-trash" title="Remove"></span></div>\
		  </div>').appendTo('#project_list');
	}
}
function load_buildconfig(name) {
	current_build_target = name;
	$('#sourcefileList').html('');
	for (var i = 0; i < project_config[name].files.length; i++) {
		var file = project_config[name].files[i];
		var parts = file.split('/'), filename = parts.pop(-1), path = parts.join('/') + '/';
		$('<li class=\'noselect\'>').html('<span class=\'path\'>'+path+'</span>'+filename).attr('id', file).appendTo('#sourcefileList');
	}
	treeview.highlight_files();
	$('#settings_compress').get(0).checked = project_config[name].compress;
	$('#settings_outputfile').val(project_config[name].outputfile);
	$('#settings_asXML').get(0).checked = project_config[name].asXML;
	$('#settings_xmlfile').val(project_config[name].xmlfile);
}
var build_targets = null;
function update_buildtarget_list() {
	$('#buildtargetList').html('');
	for (var i = 0; i < build_targets.length; i++) {
		$('<option>'+build_targets[i]+'</option>').appendTo($('#buildtargetList'));
	}
}
function load_project(e, index) {
	current_project_index = index;
	if (e !== null) {
		$('#project_list').find('.active').removeClass('active');
		$(e).addClass('active');		
	}
	$('#selectProject').hide();
	current_project = projects[index];
	console.log(current_project);
	// load config
	$.get('load_config?path=' + current_project.path, function(data){
		project_config = data;
		console.info(data);
		if (data !== null) {
			if (data === false) {
				$('#invalidPath').show();
				$('#interface').hide();
				$('#noConfig').hide();
			} else {
				$('#interface').show();
				$('#noConfig').hide();
				$('#invalidPath').hide();
				reload_tree(current_project.path);
				// insert build targets into selector
				build_targets = Object.keys(project_config);
				update_buildtarget_list();
				load_buildconfig(build_targets[0]);				
			}
		} else {
			$('#interface').hide();
			$('#invalidPath').hide();
			$('#noConfig').show();			
		}
	});
}
var awaitingConfigCreation = false;
function create_config() {
	awaitingConfigCreation = true;
	$.post('create_config', current_project.path, function(data){
		load_project(null, current_project_index);
		awaitingConfigCreation = false;
	});
}

function open_directory() {
	$.post('open_path', current_project.path);
}
var addProject_isValid = false;
var addProject_isSetup = false;
function add_project() {
	// reset form
	$('#addProject_name').val('');
	$('#addProject_path').val('');
	$('#addProject_error').hide();
	addProject_isValid = false;
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$('#dialog_addProject').show();
	$('#dialog_holder').show();
	$('#addProject_name').focus();
	// bind listeners
	if (!addProject_isSetup) {
		$('#dialog_holder, #addProject_cancel').click(function(){
			$('#dialog_holder').hide();
		});
		$('.dialog').click(function(e){
			e.stopPropagation();
		});
		$('#addProject_path').change(function(){
			$.get('validate_path?path=' + $(this).val(), function(data){
				addProject_isValid = data;
				if (data) {
					$('#addProject_path').removeClass('invalid');
					$('#addProject_error').hide();
				}
				else {
					$('#addProject_path').addClass('invalid');
					$('#addProject_error').show();
				}
			});
		});
		var submit = function(){
			if ($('#addProject_name').val().trim() === '') {
				$('#addProject_name').addClass('invalid');
			} else {
				$('#addProject_name').removeClass('invalid');
				if (addProject_isValid) {
					projects.push({
						name: $('#addProject_name').val().trim(),
						path: $('#addProject_path').val().trim()
					});
					$.post('save_projects', JSON.stringify(projects), function(){
						reload_projectlist();
						$('#dialog_holder').hide();
					});
				}
			}
		};
		$('#addProject_save').click(submit);
		$('#addProject_name').add('#addProject_path').keypress(function(e) {
			if (e.which == 13) submit();
		});
		addProject_isSetup = true;		
	}
}
var editProject_isValid = false;
var editProject_isSetup = false;
function edit_project(index) {
	// reset form
	$('#editProject_name').val(projects[index].name);
	$('#editProject_path').val(projects[index].path);
	$('#editProject_error').hide();
	editProject_isValid = true;
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$('#dialog_editProject').show();
	$('#dialog_holder').show();
	$('#editProject_name').focus();
	// bind listeners
	if (!editProject_isSetup) {
		$('#dialog_holder, #editProject_cancel').click(function(){
			$('#dialog_holder').hide();
		});
		$('.dialog').click(function(e){
			e.stopPropagation();
		});
		$('#editProject_path').change(function(){
			$.get('validate_path?path=' + $(this).val(), function(data){
				editProject_isValid = data;
				if (data) {
					$('#editProject_path').removeClass('invalid');
					$('#editProject_error').hide();
				}
				else {
					$('#editProject_path').addClass('invalid');
					$('#editProject_error').show();
				}
			});
		});
		$('#editProject_name').add('#editProject_path').keypress(function(e) {
			if (e.which == 13) $('#editProject_save').click();
		});
		editProject_isSetup = true;		
	}
	var submit = function(){
		if ($('#editProject_name').val().trim() === '') {
			$('#editProject_name').addClass('invalid');
		} else {
			$('#editProject_name').removeClass('invalid');
			if (editProject_isValid) {
				projects[index] = {
					name: $('#editProject_name').val().trim(),
					path: $('#editProject_path').val().trim()
				};
				$.post('save_projects', JSON.stringify(projects), function(){
					reload_projectlist();
					$('#dialog_holder').hide();
				});
			}
		}
	};
	$('#editProject_save').off('click');
	$('#editProject_save').on('click', submit);
}
var removeProject_isSetup = false;
function remove_project(index) {
	console.log(index);
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$('#dialog_removeProject').show();
	$('#dialog_holder').show();
	// bind listeners
	if (!removeProject_isSetup) {
		$('#dialog_holder, #removeProject_cancel').click(function(){
			$('#dialog_holder').hide();
		});
		$('.dialog').click(function(e){
			e.stopPropagation();
		});
		$('#removeProject_save').click(function(){
			projects.splice(index, 1);
			reload_projectlist();
			$('#dialog_holder').hide();
		});
		removeProject_isSetup = true;		
	}
}
var createBuildTarget_isSetup = false;
function create_buildtarget(superConf) {
	// reset form
	$('#createBuildTarget_name').val('');
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$('#dialog_createBuildTarget').show();
	$('#dialog_holder').show();
	var createBuildTarget_isValid = false;
	// bind listeners
	if (!createBuildTarget_isSetup) {
		$('#dialog_holder, #createBuildTarget_cancel').click(function(){
			$('#dialog_holder').hide();
		});
		$('.dialog').click(function(e){
			e.stopPropagation();
		});
		var submit = function() {
			if (createBuildTarget_isValid) {
				$.get('get_default_config', function(data) {
					data = data.default;
					if (superConf !== undefined) {
						console.info(data, superConf);
						data = $.extend(data, superConf);
						console.info(data);
					}
					var target_name = $('#createBuildTarget_name').val().trim();
					project_config[target_name] = data;
					build_targets.push(target_name);
					update_buildtarget_list();
					$('#buildtargetList').val(target_name);
					load_buildconfig(target_name);
					save_buildconfig();
					$('#dialog_holder').hide();
				});
			}
		};
		$('#createBuildTarget_save').click(submit);
		createBuildTarget_isSetup = true;
		$('#createBuildTarget_name').change(function(){
			createBuildTarget_isValid = build_targets.indexOf($(this).val()) < 0;
			if (build_targets.indexOf($(this).val()) >= 0) {
				$('#createBuildTarget_name').addClass('invalid');
				$('#createBuildTarget_error').show();
			} else {
				$('#createBuildTarget_name').removeClass('invalid');
				$('#createBuildTarget_error').hide();
			}
		});
	}
}
function copy_buildtarget(original) {
	if (build_targets.indexOf(original) >= 0) {
		create_buildtarget(project_config[original]);
	} else {
		alert('Invalid build target to copy from!');
	}
}

var removeBuildTarget_isSetup = false;
function remove_buildtarget(target_name) {
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$('#removeBuildTarget_name').text(target_name);
	$('#dialog_removeBuildTarget').show();
	$('#dialog_holder').show();
	// bind listeners
	if (!removeBuildTarget_isSetup) {
		$('#dialog_holder, #removeBuildTarget_cancel').click(function(){
			$('#dialog_holder').hide();
		});
		$('.dialog').click(function(e){
			e.stopPropagation();
		});
		$('#removeBuildTarget_save').click(function(){
			if (build_targets.indexOf(target_name) >= 0) {
				var afterDeletion = null;
				if (build_targets.length < 2) {
					afterDeletion = function() {
						create_buildtarget('default');
					};
				}
				delete project_config[target_name];
				build_targets.splice(build_targets.indexOf(target_name), 1);
				if (afterDeletion !== null) {
					afterDeletion();
				}
				var new_target = build_targets[0];
				update_buildtarget_list();
				$('#buildtargetList').val(new_target);
				load_buildconfig(new_target);
				save_buildconfig();
			}
			$('#dialog_holder').hide();
		});
		removeBuildTarget_isSetup = true;		
	}
}
function close_dialog() {
	$('#dialog_holder').find('.dialog').hide();
	$('#dialog_holder').hide();
}
function show_log() {
	// clear view
	$('#dialog_holder').find('.dialog').hide();
	$.get('log', function(data){
		$('#dialog_log').show();
		$('#dialog_holder').show();
		$('#logdata').html(data);
		var e = $('#logdata').get(0);
		e.scrollTop = e.scrollHeight;
	});
}
function load_projects() {
	$.get('get_projects', function(data){
		projects = data;
		reload_projectlist();
	});
}
function update_settings(element) {
	var key = element.id.split('_')[1];
	if (element.type == 'checkbox') {
		project_config[current_build_target][key] = element.checked;
	} else {
		project_config[current_build_target][key] = element.value;		
	}
	save_buildconfig();
}
function build() {
	$('#btnBuild').get(0).disabled = true;
	$.post('build', {path: current_project.path, target: current_build_target}, function(){
		$('#btnBuild').get(0).disabled = false;		
	});
}
function clear_cache() {
    $.post('clear_cache?path=' + current_project.path);
}
$(document).ready(function() {
	load_projects();
	setupFilter();
	$('#buildtargetList').change(function(){
		load_buildconfig($(this).val());
	});
	$('#sourcefileList').dragswap({
		dropComplete: function () {
			changed_sourceFiles();
		}
	});
});