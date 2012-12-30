(function (root) {

  "use strict";

  var wtf = root.WTF = {coordinates: null};

  // General interface interaction.
  wtf.display_error = function (message) {
    $("#error-message").text(message);
    $("#error").show();
  };
  wtf.hide_error = function () { $("#error").hide(); };

  // Geolocation.
  wtf.geolocate = function () {
    wtf.hide_error();
    if (Modernizr.geolocation) {
      $("#location").hide();
      navigator.geolocation.getCurrentPosition(wtf.locate.found,
                                               wtf.locate.error);
    } else {
      wtf.display_error("Geolocation isn't available.");
      $("#location-icon").hide();
    }
  };

  // Responses to geolocation.
  wtf.locate = {
    found: function (position) {
      // Update the stored coordinates.
      wtf.coordinates = {
        longitude: position.coords.longitude,
        latitude: position.coords.latitude,
        accuracy: position.coords.accuracy
      };
      wtf.get_suggestion();
    },
    error: function (err) {
      // Handle the error.
      if (err.code == 1)
        wtf.display_error("Why the fuck would you say no?");
      else
        wtf.display_error("Something went wrong with geolocation.");

      // Update the interface.
      $("#location").show();
      $("#location-icon").hide();
    }
  };

  // Manual location entry using Google geocoder API.
  wtf.geocode = function () {
    var address = $("#loc").val(),
        geocoder = new google.maps.Geocoder();

    wtf.hide_error();

    // Synchronize the interface... we don't want to accept another address
    // right away.
    $("#locform").hide();

    // Run the geocoder on the input text.
    geocoder.geocode({address: address}, function(results, code) {
      if (code == google.maps.GeocoderStatus.OK) {
        // The address was successfully resolved.
        var geomloc = results[0].geometry.location;

        // Update the stored coordinates.
        wtf.coordinates = {latitude: geomloc.lat(), longitude: geomloc.lng()};

        // Update the interface to check the address.
        $("#locconf span").text(results[0].formatted_address);
        $("#locconf").show();
      } else {
        // That wasn't even anything like an address...
        $("#locform").show();
        wtf.display_error("What the fuck kind of address is that?");
      }
    });
  };

  wtf.wrong_address = function () {
    // That address was wrong.
    $("#locconf").hide();
    $("#locform").show();
  };

  // API interaction.
  wtf.get_suggestion = function () {
    // Make sure that we *do* have coordinates of some sort.
    if (typeof wtf.coordinates === "undefined" || wtf.coordinates === null) {
      wtf.display_error("Where the fuck are you?");
      return;
    }

    // Sync the interface.
    $("#location").hide();
    $("#supertitle").hide();
    $("#title").hide();
    $("#subtitle").hide();
    $("#options").hide();

    $("#title-wrapper").off();

    // Show the loading message.
    $("#status-message").text("Hang on. I'm loading your fucking lunch preferences…")
                        .show();

    // Send the request.
    $.ajax({url: "/api/",
            data: wtf.coordinates,
            dataType: "json",
            success: wtf.suggestion.success,
            error: wtf.suggestion.error});
  };

  // API call responses.
  wtf.suggestion = {
    success: function (data, code, xhr) {
      $("#status-message").hide();

      // Show the name of the restaurant.
      $("#supertitle").text("It looks like").show();
      $("#title").html("<a href=\"" + data.url + "\" target=\"_blank\">"
                       + data.name + "</a>").show();
      $("#title-wrapper")
          .on("mouseover", function () {
            // Position the popup.
            var title_coords = $("#title").offset();
            $("#info").css({top: title_coords.top + title_coords.height - 35})
                      .show();
          })
          .on("mouseout", function () {$("#info").hide();});
      $("#subtitle").text("Is on the fucking menu for lunch.").show();

      // Show the options.
      $("#options").show();

      // Show the aggregated ratings from Yelp.
      var reviews = "reviews";
      if (data.review_count == 1) reviews = "review";
      $("#info-inner").html("<span>" + data.review_count + " " + reviews
                            + " on Yelp: </span>"
                            + "<img src=\"" + data.rating_image + "\">");

      // Show the map image.
      $("#map-img").attr("src", data.map_url);

      // List the categories.
      $("#info-categories").text(data.categories);
    },
    error: function (msg) {
      $("#status-message").hide();
      $("#supertitle").text("Hmm… Something went wrong.").show();
      $("#title").text("Maybe you should just fucking stay home.").show();
      $("#subtitle")
        .html("<a href=\"javascript:WTF.get_suggestion();\">Try again.</a>")
        .show();
    }
  };

  $(function () {
    // Check for geolocation.
    if (Modernizr.geolocation) $("#location-icon").show();
  });

})(this);
