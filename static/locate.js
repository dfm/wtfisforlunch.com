var loc = null,
    restoid = null,
    visitid = null;


// =========================================================================
//                                                         API COMMUNICATION
// =========================================================================

function render (data, code, xhr) {
  if (data.code == 1) return loc_error(data.message);
  if (data.code == 2) return error(data.message);

  $("#loading").hide();

  $("#havefun").hide();
  $("#effyeah").show();
  $("#lunch .options").show();

  $("#lunch").show();
  $("#lunch h1").html(data.name);

  restoid = data._id;
  visitid = data.vid;
}

function error(message) {
  $("#lunch").hide();
  $("#loading").hide();
  $("#error").show();
  $("#error h1").text("You broke the internet!");
  $("#error p").text(message);
}

function api_error(xhr) {
  if (xhr.status != 0)
    error("The server responded with a " + xhr.status + ".");
}

function send_request (why) {
  $("#location").hide();
  $("#error").hide();
  $("#lunch").hide();
  $("#loading").show();

  var payload = loc,
      u = "/api";
  if (arguments.length && visitid !== null) u += "/" + visitid
  $.ajax({url: u, data: payload, dataType: "json", success: render,
          error: api_error});
}


// =========================================================================
//                                                         LOCATION SERVICES
// =========================================================================

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

function loc_error (msg) {
  $("#location").show();
  $("#loading").hide();
  $("#error").hide();
  if (arguments.length && typeof msg === "string") $("#location h1").text(msg);
}

function usegeo() {
  if ("geolocation" in navigator)
    navigator.geolocation.getCurrentPosition(found, loc_error);
  loc_error();
}


// =========================================================================
//                                                                 FUCK YEAH
// =========================================================================

function proposed(data) {
}

function fuckyeah() {
  $.ajax({url: "/api/propose/" + visitid, dataType: "json",
          success: proposed, error: api_error});
  $("#havefun").show();
  $("#effyeah").hide();
  $("#lunch .options").hide();
}

function update_visit(vid, val) {
  $.ajax({url: "/api/update/" + vid + "/" + val, dataType: "json"});
  $("#header").hide();
}


// =========================================================================
//                                                                  START UP
// =========================================================================

$(function () {
  // $("#loading").show();
  $("#location").hide();
  $("#error").hide();
  $("#lunch").hide();
  usegeo();
});
