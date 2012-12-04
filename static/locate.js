var loc = null,
    restoid = null,
    visitid = null;


// =========================================================================
//                                                         API COMMUNICATION
// =========================================================================

function render (data, code, xhr) {
  if (data.code == 1) return loc_error(data.message);
  if (data.code == 2) return error(data.message);
  if (data.code == 3) return error(data.message, "You'd better just stay home…");

  $("#loading").hide();

  $("#havefun").hide();
  $("#effyeah").show();
  $("#lunch .options").show();

  $("#lunch").show();
  $("#lunch h1").html(data.name);

  var d = 0.621 * data.distance;
  if (d > 0.5) {
    var rd = "about half a mile";
    if (d > 0.75 && d <= 1) rd = "a little under a mile";
    else if (d <= 1.5) rd = "a little over a mile";
    else rd = d.toFixed(1) + " miles";
    $("#prefix").show().text("It's a fucking hike (" + rd + ") but…");
  } else $("#prefix").hide();

  restoid = data._id;
  visitid = data.vid;
}

function error(message, header) {
  $("#lunch").hide();
  $("#loading").hide();
  $("#error").show();
  if (arguments.length >= 2)
    $("#error h1").text(header);
  else
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
    if (code == google.maps.GeocoderStatus.OK) {
      var geomloc = results[0].geometry.location;
      loc = {latitude: geomloc.lat(), longitude: geomloc.lng()};
      $("#locconf span").text(results[0].formatted_address);
      $("#locconf").show();
    } else {
      loc_error("What the fuck kind of address is that?");
    }
  });
  $("#locform").hide();
  $("#usegeo").hide();
}

function found (position) {
  loc = {longitude: position.coords.longitude, latitude: position.coords.latitude,
         accuracy: position.coords.accuracy};
  send_request();
}

function loc_error (msg) {
  $("#usegeo").hide();
  $("#locconf").hide();
  $("#locform").show();
  $("#location").show();
  $("#loading").hide();
  $("#error").hide();
  if (arguments.length && typeof msg === "string") $("#location h1").text(msg);
  else $("#location h1").text("Where the fuck are you?");
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
  $("#loading").hide();
  $("#location").show();
  $("#error").hide();
  $("#lunch").hide();
});
