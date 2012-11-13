var loc = null;

function render (data, code, xhr) {
  if (data.code == 1) return loc_error();
  if (data.code == 2) return error(data.message);

  $("#loading").hide();
  $("#lunch").show();
  $("#lunch h1").html(data.name);
  $("#type").html(data.category);
}

function error(message) {
  $("#loading").hide();
  $("#error").show();
  $("#error h1").text("You broke the internet!");
  $("#error p").text(message);
}

function api_error(xhr) {
  error("The server responded with a " + xhr.status + ".");
}

function send_request () {
  $("#location").hide();
  $("#error").hide();
  $("#lunch").hide();
  $("#loading").show();
  $.ajax({url: "/api", data: loc, dataType: "json", success: render, error: api_error});
}

function update_location () {
  loc = {named: $("#loc").val()};
  send_request();
}

function found (position) {
  loc = {longitude: position.coords.longitude, latitude: position.coords.latitude,
         accuracy: position.coords.accuracy};
  send_request();
}

function loc_error () {
  $("#location").show();
  $("#loading").hide();
  $("#error").hide();
}

if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(found, loc_error);
}

$(function () {
  $("#loading").show();
  $("#location").hide();
  $("#error").hide();
  $("#lunch").hide();
});
