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
  console.log(loc);
  $.ajax({url: "/api", data: loc, dataType: "json", success: render, error: api_error});
}

function update_location () {
  var address = $("#loc").val(),
      geocoder = new google.maps.Geocoder();
  geocoder.geocode({address: address}, function(results, code) {
    console.log(results);
    if (code == google.maps.GeocoderStatus.OK) {
      var geomloc = results[0].geometry.location;
      console.log(geomloc);
      loc = {latitude: geomloc.Ya, longitude: geomloc.Za};
    } else {
      loc = {named: address};
    }
    send_request();
  });
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
