/*
 * (C) Copyright 2014 CoNWeT Lab., Universidad Politécnica de Madrid
 *
 * This file is part of CKAN Store Updater Extension.
 *
 * CKAN Store Updater Extension is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * CKAN Store Updater Extension is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public
 * License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with CKAN Store Updater Extension. If not, see
 * <http://www.gnu.org/licenses/>.
 *
 */

(function()  {
    var default_style = 'inline-block'
    var hidden_style = 'none'

    $('#field-image_upload').change(function(){
        $('#button-upload').css('display', hidden_style);
        $('#button-remove').css('display', default_style);
    });

    $('#button-remove').on('click', function(){
        // Reset file input
        var image_input = $('#field-image_upload')
        image_input.replaceWith(image_input = image_input.clone(true));
        $('#button-upload').css('display', default_style);
        $('#button-remove').css('display', hidden_style);
    });

    $('#button-upload').on('click', function() {
        $('#field-image_upload').click();
    })
})();
